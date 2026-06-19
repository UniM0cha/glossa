#!/usr/bin/env python3
"""마일스톤 A — 파일 기반 Gemini Live Translate 검증 (오디오 장치 없음).

한국어 16kHz mono 16-bit PCM WAV 한 토막을 Gemini Live Translate에 스트리밍하고,
돌아온 24kHz 번역 음성을 out_en.wav 로 저장한다. 첫 응답 지연과 원문/번역 텍스트도 출력한다.

목적: 실시간 오디오 I/O 복잡도 없이 'API가 쓸만한 번역 음성을 돌려주는가(품질·지연)'만 먼저 검증.
       → Phase 0 의 1순위 리스크를 가장 싸게 제거한다.

검증 출처(2026-06-20 확인): https://ai.google.dev/gemini-api/docs/live-api/live-translate
  - 모델 gemini-3.5-live-translate-preview / 입력 16kHz·출력 24kHz 16-bit mono PCM
  - config: LiveConnectConfig(response_modalities=["AUDIO"], translation_config=TranslationConfig(...))
  - 송신 session.send_realtime_input(audio=Blob(...)) / 수신 server_content.model_turn.parts[].inline_data.data
※ preview 모델이라 스펙이 바뀔 수 있음. 실패 시 위 문서로 재확인할 것.
"""
import argparse
import asyncio
import os
import sys
import time
import wave

from google import genai
from google.genai import types

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

MODEL = "gemini-3.5-live-translate-preview"
IN_RATE = 16000   # Gemini 입력 요구: 16kHz mono 16-bit
OUT_RATE = 24000  # Gemini 출력: 24kHz mono 16-bit
CHUNK_MS = 100    # 권장 청크 ~100ms
CHUNK_BYTES = IN_RATE * 2 * CHUNK_MS // 1000  # 16000 * 2byte * 0.1s = 3200


def read_pcm16_mono_16k(path: str) -> bytes:
    """16kHz / mono / 16-bit WAV 만 허용. 아니면 변환 안내 후 종료."""
    try:
        with wave.open(path, "rb") as w:
            ch, width, rate = w.getnchannels(), w.getsampwidth(), w.getframerate()
            frames = w.readframes(w.getnframes())
    except FileNotFoundError:
        sys.exit(f"입력 파일이 없습니다: {path}\n먼저 `./make_sample.sh` 로 샘플을 만드세요.")
    if (ch, width, rate) != (1, 2, IN_RATE):
        sys.exit(
            f"입력 WAV 포맷 불일치: channels={ch}, {width * 8}-bit, {rate}Hz\n"
            f"필요: mono / 16-bit / {IN_RATE}Hz\n"
            f"변환: afconvert -f WAVE -d LEI16@16000 -c 1 입력 출력.wav"
        )
    return frames


def write_pcm16_mono(path: str, pcm: bytes, rate: int) -> None:
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm)


async def run(in_path, out_path, target_lang, echo, idle_stop, hard_max):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        sys.exit("GEMINI_API_KEY 가 없습니다. `cp .env.example .env` 후 키를 채우거나 export 하세요.")

    pcm = read_pcm16_mono_16k(in_path)
    in_dur = len(pcm) / 2 / IN_RATE
    print(f"입력  : {in_path}  ({in_dur:.1f}s, {len(pcm)} bytes)")
    print(f"모델  : {MODEL}")
    print(f"목표어: {target_lang}  (echoTargetLanguage={echo})\n")

    client = genai.Client(api_key=api_key)
    config = types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        input_audio_transcription=types.AudioTranscriptionConfig(),
        output_audio_transcription=types.AudioTranscriptionConfig(),
        translation_config=types.TranslationConfig(
            target_language_code=target_lang,
            echo_target_language=echo,
        ),
    )

    state = {"out": bytearray(), "first_audio": None, "last_audio": None,
             "send_start": None, "in_text": [], "out_text": []}

    async with client.aio.live.connect(model=MODEL, config=config) as session:
        print("세션 시작. 실시간 페이스로 스트리밍 중...\n")

        async def sender():
            state["send_start"] = time.perf_counter()
            for i in range(0, len(pcm), CHUNK_BYTES):
                chunk = pcm[i:i + CHUNK_BYTES]
                await session.send_realtime_input(
                    audio=types.Blob(data=chunk, mime_type=f"audio/pcm;rate={IN_RATE}")
                )
                await asyncio.sleep(CHUNK_MS / 1000)  # 실제 사용과 같은 실시간 전송 페이스
            print("[송신 완료] 입력 오디오 전부 전송. 잔여 번역 음성 대기...\n")

        async def receiver():
            async for response in session.receive():
                sc = response.server_content
                if not sc:
                    continue
                if sc.input_transcription and sc.input_transcription.text:
                    state["in_text"].append(sc.input_transcription.text)
                    print(f"  [원문 ko] {sc.input_transcription.text}")
                if sc.output_transcription and sc.output_transcription.text:
                    state["out_text"].append(sc.output_transcription.text)
                    print(f"  [번역 {target_lang}] {sc.output_transcription.text}")
                if sc.model_turn:
                    for part in sc.model_turn.parts:
                        if part.inline_data and part.inline_data.data:
                            now = time.perf_counter()
                            if state["first_audio"] is None:
                                state["first_audio"] = now
                                print(f"  >>> 첫 번역 음성 수신 (지연 {now - state['send_start']:.2f}s)")
                            state["last_audio"] = now
                            state["out"].extend(part.inline_data.data)

        recv = asyncio.create_task(receiver())
        await sender()

        # 잔여 응답 드레인: 마지막 음성 후 idle_stop초 지나거나 hard_max 초과 시 종료
        send_done = time.perf_counter()
        while True:
            await asyncio.sleep(0.25)
            now = time.perf_counter()
            if recv.done():
                break
            if now - send_done > hard_max:
                print(f"[종료] 송신 후 최대 대기 {hard_max:.0f}s 초과.")
                break
            last = state["last_audio"]
            if last is not None and now - last > idle_stop:
                print(f"[종료] {idle_stop:.0f}s 동안 추가 음성 없음.")
                break
        recv.cancel()

    out = bytes(state["out"])
    print()
    if not out:
        print("경고: 번역 음성을 한 바이트도 받지 못했습니다. 모델 ID/키/네트워크/SDK 버전을 확인하세요.")
        return
    write_pcm16_mono(out_path, out, OUT_RATE)
    out_dur = len(out) / 2 / OUT_RATE

    print("─" * 48)
    print(f"저장      : {out_path}  ({out_dur:.1f}s, {len(out)} bytes)")
    if state["first_audio"]:
        print(f"첫응답지연: {state['first_audio'] - state['send_start']:.2f}s")
    print(f"원문 ko   : {' '.join(state['in_text']) or '(전사 없음)'}")
    print(f"번역 {target_lang:6}: {' '.join(state['out_text']) or '(전사 없음)'}")
    print("─" * 48)
    print(f"\n재생: afplay {out_path}   (귀로 번역 품질·억양 보존 확인)")


def main():
    ap = argparse.ArgumentParser(description="파일 기반 Gemini Live Translate 검증 (마일스톤 A)")
    ap.add_argument("-i", "--input", default="samples/sermon_ko_16k.wav", help="입력 WAV (16kHz mono 16-bit)")
    ap.add_argument("-o", "--output", default="out_en.wav", help="번역 음성 출력 WAV")
    ap.add_argument("-l", "--lang", default="en", help="목표 언어 BCP-47 코드 (기본 en)")
    ap.add_argument("--echo", action="store_true", help="echoTargetLanguage 켜기 (이미 목표어인 입력을 따라 말함)")
    ap.add_argument("--idle-stop", type=float, default=3.0, help="추가 음성 없을 때 종료 임계(초)")
    ap.add_argument("--hard-max", type=float, default=30.0, help="송신 완료 후 최대 대기(초)")
    args = ap.parse_args()
    asyncio.run(run(args.input, args.output, args.lang, args.echo, args.idle_stop, args.hard_max))


if __name__ == "__main__":
    main()

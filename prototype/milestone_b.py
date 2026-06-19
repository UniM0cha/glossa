#!/usr/bin/env python3
"""마일스톤 B — 실시간 마이크 → 영어 통역 (라이브 플레이백).

기본 입력 장치(마이크)에서 한국어를 16kHz mono PCM 으로 캡처 → Gemini Live Translate →
돌아온 24kHz 영어 음성을 기본 출력 장치로 실시간 재생한다. Ctrl+C 로 종료.

⚠️ 반드시 '이어폰/헤드폰' 사용을 권장. 스피커로 출력하면 번역 음성이 다시 마이크로 들어가
   피드백 루프가 생긴다 (상위 README 불변규칙 #2).

검증 출처(2026-06-20): https://ai.google.dev/gemini-api/docs/live-api/live-translate
"""
import argparse
import asyncio
import os
import sys
import threading

import sounddevice as sd
from google import genai
from google.genai import types

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

MODEL = "gemini-3.5-live-translate-preview"
IN_RATE = 16000   # Gemini 입력: 16kHz mono 16-bit
OUT_RATE = 24000  # Gemini 출력: 24kHz mono 16-bit
BLOCK = 1600      # 100ms @ 16kHz (권장 청크)


def mic_check(seconds=1.5, device=None):
    """마이크가 실제로 소리를 받는지(권한/연결) 확인. RMS 가 0 에 가까우면 입력이 안 들어오는 것.

    실시간 경로와 동일하게 RawInputStream + stdlib 만 사용(numpy/sd.rec 불필요).
    """
    import array
    print(f"마이크 점검: {seconds}s 동안 입력 레벨 측정 중... (조용히 있거나 말해 보세요)")
    chunks = []
    with sd.RawInputStream(samplerate=IN_RATE, blocksize=BLOCK, dtype="int16",
                           channels=1, device=device,
                           callback=lambda indata, n, t, s: chunks.append(bytes(indata))):
        sd.sleep(int(seconds * 1000))
    samples = array.array("h")
    samples.frombytes(b"".join(chunks))
    rms = (sum(x * x for x in samples) / len(samples)) ** 0.5 if samples else 0.0
    print(f"  입력 RMS = {rms:.1f}  (샘플 {len(samples)})")
    if rms < 5:
        print("  ⚠️ 입력 레벨이 0에 가깝습니다 — 마이크 권한 미허용/장치 문제일 수 있습니다.")
        print("     이 경우 사용자님 터미널에서 직접 실행해 마이크 권한을 허용하세요.")
    return rms


async def run(target_lang, echo, in_dev, out_dev):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        sys.exit("GEMINI_API_KEY 가 없습니다. .env 를 확인하세요.")

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

    loop = asyncio.get_running_loop()
    in_q: asyncio.Queue = asyncio.Queue()
    out_buf = bytearray()
    out_lock = threading.Lock()

    def in_cb(indata, frames, time_info, status):
        # PortAudio 스레드. 복사해서 asyncio 큐로 넘김(콜백 비블로킹).
        loop.call_soon_threadsafe(in_q.put_nowait, bytes(indata))

    def out_cb(outdata, frames, time_info, status):
        # PortAudio 스레드. 버퍼에서 필요한 만큼 꺼내 채우고, 모자라면 무음.
        need = frames * 2
        with out_lock:
            n = min(need, len(out_buf))
            chunk = bytes(out_buf[:n])
            del out_buf[:n]
        if n < need:
            chunk += b"\x00" * (need - n)
        outdata[:] = chunk

    in_stream = sd.RawInputStream(samplerate=IN_RATE, blocksize=BLOCK, dtype="int16",
                                  channels=1, callback=in_cb, device=in_dev)
    out_stream = sd.RawOutputStream(samplerate=OUT_RATE, blocksize=0, dtype="int16",
                                    channels=1, callback=out_cb, device=out_dev)

    async with client.aio.live.connect(model=MODEL, config=config) as session:
        print(f"● 실시간 통역 시작 (ko → {target_lang}). 말씀하세요. (Ctrl+C 종료)\n")
        in_stream.start()
        out_stream.start()

        async def sender():
            while True:
                b = await in_q.get()
                await session.send_realtime_input(
                    audio=types.Blob(data=b, mime_type=f"audio/pcm;rate={IN_RATE}")
                )

        async def receiver():
            async for response in session.receive():
                sc = response.server_content
                if not sc:
                    continue
                if sc.input_transcription and sc.input_transcription.text:
                    print(f"  [ko] {sc.input_transcription.text}")
                if sc.output_transcription and sc.output_transcription.text:
                    print(f"  [{target_lang}] {sc.output_transcription.text}")
                if sc.model_turn:
                    for part in sc.model_turn.parts:
                        if part.inline_data and part.inline_data.data:
                            with out_lock:
                                out_buf.extend(part.inline_data.data)

        try:
            await asyncio.gather(sender(), receiver())
        finally:
            for s in (in_stream, out_stream):
                try:
                    s.stop(); s.close()
                except Exception:
                    pass


def main():
    ap = argparse.ArgumentParser(description="실시간 마이크→영어 통역 (마일스톤 B)")
    ap.add_argument("-l", "--lang", default="en", help="목표 언어 BCP-47 (기본 en)")
    ap.add_argument("--echo", action="store_true", help="echoTargetLanguage 켜기")
    ap.add_argument("--in-dev", default=None, help="입력 장치(번호/이름). 미지정 시 기본 마이크")
    ap.add_argument("--out-dev", default=None, help="출력 장치(번호/이름). 미지정 시 기본 출력")
    ap.add_argument("--list-devices", action="store_true", help="오디오 장치 목록 출력 후 종료")
    ap.add_argument("--check-mic", action="store_true", help="마이크 입력 레벨만 점검 후 종료")
    args = ap.parse_args()

    if args.list_devices:
        print(sd.query_devices())
        return

    def parse_dev(v):
        if v is None:
            return None
        return int(v) if v.isdigit() else v

    in_dev, out_dev = parse_dev(args.in_dev), parse_dev(args.out_dev)

    if args.check_mic:
        mic_check(device=in_dev)
        return

    try:
        asyncio.run(run(args.lang, args.echo, in_dev, out_dev))
    except KeyboardInterrupt:
        print("\n종료.")


if __name__ == "__main__":
    main()

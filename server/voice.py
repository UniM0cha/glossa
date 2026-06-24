"""번역 transcript 델타 → 문장 buffering → 설교자 음색 TTS(eleven_multilingual_v2) → PCM.

실시간 통역의 음색 변환 단계. on_transcript 콜백에서 feed(lang, delta) 로 델타를 넣으면
문장 경계마다 ElevenLabs TTS 로 합성해 send(lang, pcm) 으로 송출한다.

설계:
- 언어별 단일 워커 큐로 **직렬 처리** → 문장 순서 보장(설교 순서 중요).
- ElevenLabs SDK 는 sync → asyncio.to_thread 로 호출해 이벤트 루프/콜백 비블로킹(아키텍처 규칙 3).
- 출력 pcm_24000 = 24kHz PCM16 mono → 기존 폰/웹 재생 경로 무변경.
- Phase B 확정: eleven_multilingual_v2 + sim 1.0 + speaker_boost + speed 0.8.
"""
import asyncio
import logging
import os
import re

from elevenlabs import ElevenLabs, VoiceSettings

log = logging.getLogger("voice")

TTS_MODEL = "eleven_multilingual_v2"
OUT_RATE = 24000
VOICE_SETTINGS = VoiceSettings(stability=0.5, similarity_boost=1.0,
                               use_speaker_boost=True, speed=0.8)

# 설교자 → voice_id (Phase B 확정, ElevenLabs IVC). voice_id 는 비밀이 아님.
SPEAKERS = {
    "chae": "2fCeiuAwCP4TyD4PVady",   # 채성렬
    "lee":  "DUzFhVH4D9VyWzKVHkCy",   # 이호균
    "kwon": "q4EzawyLqa1Ia3P8xqHT",   # 권순호
}

# 문장 경계: .!? (닫는 따옴표/괄호 허용) 뒤 공백 또는 끝
_SENT = re.compile(r'(.+?[.!?]["\')\]]?)(\s+|$)', re.S)


class VoiceConverter:
    """transcript 델타를 문장 단위로 모아 설교자 음색으로 합성·송출."""

    def __init__(self, send, api_key=None):
        self.send = send                              # async fn(lang, pcm_bytes)
        self.client = ElevenLabs(api_key=api_key or os.environ.get("ELEVENLABS_API_KEY"))
        self.speaker = None                           # 현재 설교자 key('chae'..)
        self.voice_id = None                          # 현재 설교자 voice_id (None=비활성)
        self.buffers: dict[str, str] = {}             # lang -> 미완성 텍스트
        self.queues: dict[str, asyncio.Queue] = {}
        self.workers: dict[str, asyncio.Task] = {}

    def set_speaker(self, speaker):
        """speaker key('chae'..) 또는 None. None 이면 음색 변환 비활성."""
        self.speaker = speaker
        self.voice_id = SPEAKERS.get(speaker) if speaker else None
        log.info("voice 설교자=%s (voice_id=%s)", speaker, self.voice_id)

    @property
    def enabled(self):
        return self.voice_id is not None

    def feed(self, lang, delta):
        """transcript 델타 누적 → 완성된 문장을 큐에 넣는다(미완성은 buffer 유지)."""
        if not self.enabled or not delta:
            return
        buf = self.buffers.get(lang, "") + delta
        last = 0
        for m in _SENT.finditer(buf):
            sentence = m.group(1).strip()
            if sentence:
                self._enqueue(lang, sentence)
            last = m.end()
        self.buffers[lang] = buf[last:]

    def flush(self, lang):
        """남은 미완성 텍스트를 강제로 합성(세션/문단 종료 시)."""
        rest = self.buffers.get(lang, "").strip()
        if rest and self.enabled:
            self._enqueue(lang, rest)
        self.buffers[lang] = ""

    def reset(self, lang=None):
        """버퍼 비우기(설교자 전환 등). lang=None 이면 전체."""
        if lang is None:
            self.buffers.clear()
        else:
            self.buffers.pop(lang, None)

    def _enqueue(self, lang, text):
        q = self.queues.get(lang)
        if q is None:
            q = asyncio.Queue()
            self.queues[lang] = q
            self.workers[lang] = asyncio.create_task(self._worker(lang, q))
        q.put_nowait((self.voice_id, text))

    async def _worker(self, lang, q):
        while True:
            voice_id, text = await q.get()
            try:
                pcm = await asyncio.to_thread(self._convert, voice_id, lang, text)
                if pcm:
                    await self.send(lang, pcm)
            except Exception as e:
                log.warning("[%s] TTS 실패: %s", lang, repr(e)[:180])
            finally:
                q.task_done()

    def _convert(self, voice_id, lang, text):
        chunks = self.client.text_to_speech.convert(
            voice_id=voice_id, text=text, model_id=TTS_MODEL,
            output_format="pcm_24000", language_code=lang,
            voice_settings=VOICE_SETTINGS)
        return b"".join(chunks)


if __name__ == "__main__":
    # 단위 테스트: transcript 델타 시뮬 → 문장 분할·순서·합성 검증 → wav 저장
    import wave
    from dotenv import load_dotenv

    HERE = os.path.dirname(os.path.abspath(__file__))
    ROOT = os.path.dirname(HERE)
    load_dotenv(os.path.join(HERE, ".env"))
    logging.basicConfig(level=logging.INFO)

    async def main():
        out = []

        async def sink(lang, pcm):
            out.append(pcm)
            print(f"  송출 #{len(out)}: {len(pcm)/2/24000:.1f}s")

        vc = VoiceConverter(sink)
        vc.set_speaker("chae")
        text = ("For God so loved the world that He gave His only Son. "
                "Whoever believes in Him shall not perish, but have eternal life. "
                "This is the very heart of the gospel.")
        for w in text.split(" "):       # 델타 흉내(단어 단위)
            vc.feed("en", w + " ")
            await asyncio.sleep(0.03)
        vc.flush("en")
        for q in vc.queues.values():     # 큐가 다 비워질 때까지 대기
            await q.join()
        pcm = b"".join(out)
        p = os.path.join(ROOT, "prototype", "voices", "vc_unit_test.wav")
        with wave.open(p, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(24000)
            w.writeframes(pcm)
        print(f"문장 {len(out)}개 합성, 총 {len(pcm)/2/24000:.1f}s → {p}")

    asyncio.run(main())

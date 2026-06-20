"""언어별 Gemini Live Translate 세션 fan-out + 구독자 게이팅.

핵심 규칙:
- 한 언어 = google-genai Live 세션 1개. 같은 언어 청취자들은 이 세션 출력을 공유.
- 세션은 (서비스 LIVE) AND (그 언어 구독자 ≥ 1) 일 때만 ON → 낭비/비용 방지.
- 공유 한국어 16k PCM 을 활성 세션 전부에 fan-out 입력.

Phase 0 prototype/milestone_b.py 의 Gemini config·송수신 패턴 재사용.
검증 출처(2026-06-20): https://ai.google.dev/gemini-api/docs/live-api/live-translate
"""
import asyncio
import logging
import os

from google import genai
from google.genai import types

log = logging.getLogger("session")

MODEL = "gemini-3.5-live-translate-preview"
IN_RATE = 16000   # Gemini 입력: 16kHz mono 16-bit
OUT_RATE = 24000  # Gemini 출력: 24kHz mono 16-bit


class LanguageSession:
    """한 목표 언어에 대한 Gemini Live 세션. 공유 한국어 PCM 입력 → 번역 PCM broadcast."""

    def __init__(self, lang, client, broadcast, on_transcript=None):
        self.lang = lang
        self.client = client
        self.broadcast = broadcast          # async fn(lang, pcm_bytes)
        self.on_transcript = on_transcript  # optional async fn(lang, text)
        self.in_q: asyncio.Queue = asyncio.Queue()
        self._task = None
        self._running = False

    def feed(self, pcm: bytes):
        if self._running:
            self.in_q.put_nowait(pcm)

    async def start(self):
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run())
        log.info("[%s] 세션 시작", self.lang)

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        while not self.in_q.empty():
            self.in_q.get_nowait()
        log.info("[%s] 세션 종료", self.lang)

    async def _run(self):
        config = types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            output_audio_transcription=types.AudioTranscriptionConfig(),
            translation_config=types.TranslationConfig(
                target_language_code=self.lang,
                echo_target_language=False,
            ),
        )
        try:
            async with self.client.aio.live.connect(model=MODEL, config=config) as session:
                async def sender():
                    while True:
                        pcm = await self.in_q.get()
                        await session.send_realtime_input(
                            audio=types.Blob(data=pcm, mime_type=f"audio/pcm;rate={IN_RATE}")
                        )

                async def receiver():
                    async for response in session.receive():
                        sc = response.server_content
                        if not sc:
                            continue
                        if sc.output_transcription and sc.output_transcription.text and self.on_transcript:
                            await self.on_transcript(self.lang, sc.output_transcription.text)
                        if sc.model_turn:
                            for part in sc.model_turn.parts:
                                if part.inline_data and part.inline_data.data:
                                    await self.broadcast(self.lang, part.inline_data.data)

                await asyncio.gather(sender(), receiver())
        except asyncio.CancelledError:
            raise
        except Exception as e:  # 세션 오류 시 죽지 않고 로그 (재접속은 상위에서)
            log.exception("[%s] 세션 오류: %s", self.lang, e)


class SessionManager:
    def __init__(self, broadcast, on_transcript=None):
        self.broadcast = broadcast
        self.on_transcript = on_transcript
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY 가 없습니다 (.env 확인)")
        self.client = genai.Client(api_key=api_key)
        self.sessions: dict[str, LanguageSession] = {}
        self.subs: dict[str, int] = {}
        self.live = False
        self._lock = asyncio.Lock()

    def feed_korean(self, pcm: bytes):
        for s in self.sessions.values():
            s.feed(pcm)

    async def set_live(self, live: bool):
        self.live = live
        await self._reconcile()

    async def add_subscriber(self, lang: str):
        self.subs[lang] = self.subs.get(lang, 0) + 1
        await self._reconcile()

    async def remove_subscriber(self, lang: str):
        self.subs[lang] = max(0, self.subs.get(lang, 0) - 1)
        await self._reconcile()

    def active_langs(self):
        return sorted(self.sessions.keys())

    async def _reconcile(self):
        """각 언어 세션을 (live AND 구독자>0) 상태에 맞춘다."""
        async with self._lock:
            langs = set(self.subs) | set(self.sessions)
            for lang in langs:
                should = self.live and self.subs.get(lang, 0) > 0
                running = lang in self.sessions
                if should and not running:
                    s = LanguageSession(lang, self.client, self.broadcast, self.on_transcript)
                    self.sessions[lang] = s
                    await s.start()
                elif not should and running:
                    s = self.sessions.pop(lang)
                    await s.stop()

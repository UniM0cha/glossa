#!/usr/bin/env python3
"""가짜 폰 청취자 — /listen 검증용.

서버의 /listen?lang= 에 접속해 상태(JSON)와 번역 음성(24k PCM)을 받아 WAV 로 저장.
첫 오디오 지연도 출력. 브라우저 없이 서버 출력 경로 검증.

  python test_listener.py            # 기본 en
  python test_listener.py vi out_vi.wav
"""
import asyncio
import sys
import time
import wave

import websockets

OUT_RATE = 24000


async def main():
    lang = sys.argv[1] if len(sys.argv) > 1 else "en"
    out = sys.argv[2] if len(sys.argv) > 2 else f"out_{lang}.wav"
    base = sys.argv[3] if len(sys.argv) > 3 else "ws://localhost:8000"
    url = f"{base}/listen?lang={lang}"

    buf = bytearray()
    first = None
    t0 = time.perf_counter()
    print(f"연결: {url}")
    async with websockets.connect(url) as ws:
        print("listen 연결됨. 수신 대기...")
        try:
            while True:
                msg = await asyncio.wait_for(ws.recv(), timeout=25)
                if isinstance(msg, (bytes, bytearray)):
                    if first is None:
                        first = time.perf_counter()
                        print(f">>> 첫 번역 음성 수신 ({first - t0:.2f}s)")
                    buf.extend(msg)
                else:
                    print(f"status: {msg}")
        except asyncio.TimeoutError:
            print("25s 무음 → 종료")

    with wave.open(out, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(OUT_RATE)
        w.writeframes(bytes(buf))
    print(f"저장 {out}  ({len(buf)} bytes, {len(buf)/2/OUT_RATE:.1f}s)")


if __name__ == "__main__":
    asyncio.run(main())

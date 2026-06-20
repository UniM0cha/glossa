#!/usr/bin/env python3
"""가짜 OBS 플러그인 — 인그레스 검증용.

OBS/C++ 플러그인 없이, prototype 의 한국어 샘플 WAV(16k mono s16)를 100ms 청크로
/ingress 에 실시간 페이스로 업로드한다. 서버 단독 end-to-end(M2.0) 검증에 사용.

  python fake_plugin.py                       # 기본 localhost
  python fake_plugin.py ws://host:8000        # 다른 서버
"""
import asyncio
import os
import sys
import wave

import websockets
from dotenv import load_dotenv

load_dotenv()

HERE = os.path.dirname(os.path.abspath(__file__))
WAV = os.path.join(HERE, "..", "prototype", "samples", "sermon_ko_16k.wav")
SERVICE_KEY = os.environ.get("SERVICE_KEY", "changeme")
CHUNK = 3200  # 100ms @ 16kHz s16 mono


async def main():
    base = sys.argv[1] if len(sys.argv) > 1 else "ws://localhost:8000"
    url = f"{base}/ingress?key={SERVICE_KEY}"

    with wave.open(WAV, "rb") as w:
        if (w.getnchannels(), w.getsampwidth(), w.getframerate()) != (1, 2, 16000):
            sys.exit("샘플 WAV 포맷 오류: 16kHz mono s16 가 아닙니다. prototype/make_sample.sh 실행 필요.")
        pcm = w.readframes(w.getnframes())

    print(f"연결: {url}")
    async with websockets.connect(url) as ws:
        print(f"ingress 연결됨 → {len(pcm)} bytes 송신 시작 ({len(pcm)/2/16000:.1f}s)")
        for i in range(0, len(pcm), CHUNK):
            await ws.send(pcm[i:i + CHUNK])
            await asyncio.sleep(0.1)  # 실시간 페이스
        print("송신 완료. 잔여 번역 대기 위해 5s 유지...")
        await asyncio.sleep(5)
    print("종료(서비스 IDLE 전환).")


if __name__ == "__main__":
    asyncio.run(main())

"""모델별 TTS 지연 측정 — 실시간 통역 적합성 판단.

TTFB(첫 청크까지) = 실시간 체감 지연의 핵심. 전체 시간·실시간 배수도 측정.
streaming API 로 첫 바이트 도착 시각을 잰다. 각 모델 2회 측정해 평균 경향 확인.
"""
import json
import os
import time

from dotenv import load_dotenv
from elevenlabs import ElevenLabs, VoiceSettings

ROOT = "/Users/solstice/Desktop/Toys/obs-live-interpreter"
load_dotenv(f"{ROOT}/server/.env.local")
client = ElevenLabs(api_key=os.environ["ELEVENLABS_API_KEY"])
voices = json.load(open(f"{ROOT}/prototype/voices/voices.json"))
vid = voices["chae"]["voice_id"]

TEXT = ("The scripture we're sharing today is John 3:16. "
        "For God so loved the world that He gave His only begotten Son, "
        "that whoever believes in Him shall not perish.")
MODELS = ["eleven_flash_v2_5", "eleven_turbo_v2_5", "eleven_multilingual_v2", "eleven_v3"]
VS = VoiceSettings(stability=0.5, similarity_boost=0.9, speed=0.8)


def measure(model):
    t0 = time.time()
    first = None
    nbytes = 0
    for chunk in client.text_to_speech.stream(
            voice_id=vid, text=TEXT, model_id=model,
            output_format="pcm_24000", language_code="en", voice_settings=VS):
        if first is None:
            first = time.time() - t0
        nbytes += len(chunk)
    total = time.time() - t0
    audio_s = nbytes / 2 / 24000
    return first, total, audio_s


print(f"{'model':24} {'TTFB':>8} {'전체':>7} {'오디오':>7}")
print("-" * 52)
for model in MODELS:
    try:
        # 2회 측정 후 더 빠른 쪽(워밍업 영향 배제)
        runs = [measure(model) for _ in range(2)]
        first = min(r[0] for r in runs)
        total = min(r[1] for r in runs)
        audio_s = runs[0][2]
        print(f"{model:24} {first*1000:6.0f}ms {total:6.1f}s {audio_s:6.1f}s")
    except Exception as e:
        print(f"{model:24} ERR {repr(e)[:120]}")

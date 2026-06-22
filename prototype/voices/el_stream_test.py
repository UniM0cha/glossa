"""입력 텍스트 스트리밍(convert_realtime) 모델별 지원·지연 실측.

live translation transcript 델타를 시뮬레이션(단어 단위로 흘려보냄) → convert_realtime.
어떤 모델이 WebSocket 입력 스트리밍을 지원하는지(특히 eleven_v3) + 스트리밍 TTFB 확인.
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


def transcript_delta():
    """번역 transcript 델타 흉내 — 단어 단위로 흘려보냄."""
    for w in TEXT.split(" "):
        yield w + " "
        time.sleep(0.05)


print(f"{'model':24} {'결과':>6} {'TTFB':>8} {'오디오':>7}")
print("-" * 50)
for model in MODELS:
    try:
        t0 = time.time()
        first = None
        nbytes = 0
        for audio in client.text_to_speech.convert_realtime(
                voice_id=vid, text=transcript_delta(), model_id=model,
                output_format="pcm_24000", voice_settings=VS):
            if first is None:
                first = time.time() - t0
            nbytes += len(audio)
        print(f"{model:24} {'OK':>6} {first*1000:6.0f}ms {nbytes/2/24000:6.1f}s")
    except Exception as e:
        print(f"{model:24} {'ERR':>6}  {repr(e)[:110]}")

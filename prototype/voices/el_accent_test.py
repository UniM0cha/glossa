"""억양("인도식 영어") 개선 비교 — chae 보이스로 모델별 생성.

cross-lingual cloning 에서 한국어 샘플 voice가 영어를 발화할 때 억양이 모델에 좌우.
eleven_v3(최신, 표현·억양 제어 우수) vs multilingual_v2(현재) vs turbo. speed 0.8, sim 0.9 고정.
"""
import json
import os
import wave

from dotenv import load_dotenv
from elevenlabs import ElevenLabs, VoiceSettings

ROOT = "/Users/solstice/Desktop/Toys/obs-live-interpreter"
load_dotenv(f"{ROOT}/server/.env")
client = ElevenLabs(api_key=os.environ["ELEVENLABS_API_KEY"])
voices = json.load(open(f"{ROOT}/prototype/voices/voices.json"))
vid = voices["chae"]["voice_id"]

TEXT = ("The scripture we're sharing today is John 3:16. "
        "For God so loved the world that He gave His only begotten Son, "
        "that whoever believes in Him shall not perish.")
OUT = f"{ROOT}/prototype/voices/ab_accent"
os.makedirs(OUT, exist_ok=True)

MODELS = ["eleven_multilingual_v2", "eleven_v3", "eleven_turbo_v2_5"]


def save(pcm, p):
    with wave.open(p, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(24000)
        w.writeframes(pcm)


for model in MODELS:
    try:
        pcm = b"".join(client.text_to_speech.convert(
            voice_id=vid, text=TEXT, model_id=model,
            output_format="pcm_24000", language_code="en",
            voice_settings=VoiceSettings(stability=0.5, similarity_boost=0.9, speed=0.8)))
        save(pcm, f"{OUT}/chae_{model}.wav")
        print(f"{model}: {len(pcm)/2/24000:.1f}s OK")
    except Exception as e:
        print(f"{model}: ERR {repr(e)[:160]}")

print("결과:", OUT)

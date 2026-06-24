"""음질("웅웅대는" 부밍) 개선 비교 — chae 보이스로 모델·similarity 조합 생성.

가설: flash_v2_5(저지연·저음질) + 높은 similarity_boost(입력 PA 음향 과복제)가 부밍 원인.
→ multilingual_v2(고음질)·낮은 similarity 로 비교. speed=0.8 공통.
"""
import json
import os
import wave

from dotenv import load_dotenv
from elevenlabs import ElevenLabs, VoiceSettings

ROOT = "/Users/solstice/Desktop/Toys/glossa"
load_dotenv(f"{ROOT}/server/.env")
client = ElevenLabs(api_key=os.environ["ELEVENLABS_API_KEY"])
voices = json.load(open(f"{ROOT}/prototype/voices/voices.json"))
vid = voices["chae"]["voice_id"]

TEXT = ("The scripture we're sharing today is John 3:16. "
        "For God so loved the world that He gave His only begotten Son, "
        "that whoever believes in Him shall not perish.")
OUT = f"{ROOT}/prototype/voices/ab_quality"
os.makedirs(OUT, exist_ok=True)

# (이름, 모델, similarity_boost)
CONFIGS = [
    ("flash_sim90", "eleven_flash_v2_5", 0.9),       # 현재(웅웅 의심)
    ("flash_sim50", "eleven_flash_v2_5", 0.5),
    ("multi_sim75", "eleven_multilingual_v2", 0.75),
    ("multi_sim90", "eleven_multilingual_v2", 0.9),
    ("multi_sim50", "eleven_multilingual_v2", 0.5),
]


def save(pcm, p):
    with wave.open(p, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(24000)
        w.writeframes(pcm)


for name, model, sim in CONFIGS:
    pcm = b"".join(client.text_to_speech.convert(
        voice_id=vid, text=TEXT, model_id=model,
        output_format="pcm_24000", language_code="en",
        voice_settings=VoiceSettings(stability=0.5, similarity_boost=sim, speed=0.8)))
    save(pcm, f"{OUT}/chae_{name}.wav")
    print(f"{name:14} ({model}, sim={sim}): {len(pcm)/2/24000:.1f}s")

print("결과:", OUT)

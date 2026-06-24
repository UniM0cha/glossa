"""eleven_v3 유사도 끌어올리기 — stability/similarity_boost/speaker_boost 조합 비교.

v3는 stability 0.0/0.5/1.0 ≈ Creative/Natural/Robust. Robust(1.0)가 원본 voice에 가장 충실.
유사도가 아쉬울 때 sim=1.0 + speaker_boost + 높은 stability 로 음색을 끌어올린다.
비교 기준으로 multilingual_v2(유사도 좋았던) 도 함께 생성. speed 0.8 공통.
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
OUT = f"{ROOT}/prototype/voices/ab_v3sim"
os.makedirs(OUT, exist_ok=True)

# (이름, 모델, stability, similarity_boost)
CONFIGS = [
    ("v3_stab100_sim100", "eleven_v3", 1.0, 1.0),
    ("v3_stab50_sim100", "eleven_v3", 0.5, 1.0),
    ("v3_stab100_sim90", "eleven_v3", 1.0, 0.9),
    ("v2_sim100", "eleven_multilingual_v2", 0.5, 1.0),  # 유사도 비교 기준
]


def save(pcm, p):
    with wave.open(p, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(24000)
        w.writeframes(pcm)


for name, model, stab, sim in CONFIGS:
    try:
        pcm = b"".join(client.text_to_speech.convert(
            voice_id=vid, text=TEXT, model_id=model,
            output_format="pcm_24000", language_code="en",
            voice_settings=VoiceSettings(stability=stab, similarity_boost=sim,
                                         speed=0.8, use_speaker_boost=True)))
        save(pcm, f"{OUT}/chae_{name}.wav")
        print(f"{name:20} ({model}, stab={stab}, sim={sim}): {len(pcm)/2/24000:.1f}s")
    except Exception as e:
        print(f"{name}: ERR {repr(e)[:160]}")

print("결과:", OUT)

"""TTS 발화 속도 비교 — chae 보이스로 speed 값을 바꿔가며 생성.

ElevenLabs VoiceSettings.speed: 0.7~1.2 (기본 1.0, 낮을수록 느림).
similarity_boost 를 높여 유사도도 함께 끌어올린다.
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
OUT = f"{ROOT}/prototype/voices/ab_speed"
os.makedirs(OUT, exist_ok=True)


def save(pcm, p):
    with wave.open(p, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(24000)
        w.writeframes(pcm)


for sp in (1.0, 0.9, 0.85, 0.8):
    pcm = b"".join(client.text_to_speech.convert(
        voice_id=vid, text=TEXT, model_id="eleven_flash_v2_5",
        output_format="pcm_24000", language_code="en",
        voice_settings=VoiceSettings(stability=0.5, similarity_boost=0.9, speed=sp)))
    save(pcm, f"{OUT}/chae_speed{sp}.wav")
    print(f"speed={sp}: {len(pcm)/2/24000:.1f}s")

print("결과:", OUT)

"""나머지 TTS 모델 비교 — turbo_v2_5 / flash_v2_5 / multilingual_v1.

v2와 동일 조건(stab=0.5, sim=1.0, speaker_boost, speed=0.8) + 같은 평범 문장(s1,s2).
v2 기준본은 ab_v3plain/chae_s1_v2.wav, chae_s2_v2.wav 참고.
"""
import json
import os
import wave

from dotenv import load_dotenv
from elevenlabs import ElevenLabs, VoiceSettings

ROOT = "/Users/solstice/Desktop/Toys/obs-live-interpreter"
load_dotenv(f"{ROOT}/server/.env.local")
client = ElevenLabs(api_key=os.environ["ELEVENLABS_API_KEY"])
voices = json.load(open(f"{ROOT}/prototype/voices/voices.json"))
vid = voices["chae"]["voice_id"]

OUT = f"{ROOT}/prototype/voices/ab_models"
os.makedirs(OUT, exist_ok=True)

SENTENCES = {
    "s1": ("The book of Romans was written by the apostle Paul to the believers in the city of Rome. "
           "In this letter, he explains the foundation of the gospel and what it means to live by faith."),
    "s2": ("In the beginning, God created the heavens and the earth. "
           "He made the light and the darkness, the land and the sea, "
           "and everything that lives and breathes upon it."),
}
MODELS = ["eleven_turbo_v2_5", "eleven_flash_v2_5", "eleven_multilingual_v1"]
VS = VoiceSettings(stability=0.5, similarity_boost=1.0, use_speaker_boost=True, speed=0.8)


def save(pcm, p):
    with wave.open(p, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(24000)
        w.writeframes(pcm)


for sname, text in SENTENCES.items():
    for model in MODELS:
        short = model.replace("eleven_", "")
        try:
            pcm = b"".join(client.text_to_speech.convert(
                voice_id=vid, text=text, model_id=model,
                output_format="pcm_24000", language_code="en", voice_settings=VS))
            save(pcm, f"{OUT}/chae_{sname}_{short}.wav")
            print(f"{sname} {short}: {len(pcm)/2/24000:.1f}s")
        except Exception as e:
            print(f"{sname} {short}: ERR {repr(e)[:130]}")

print("결과:", OUT)

"""chae v3 유사도 판단용 추가 샘플 — 톤이 다른 설교 문장 3개.

설정 고정: eleven_v3, stability=1.0(Robust), similarity_boost=1.0, speaker_boost, speed=0.8.
차분/격정/위로 톤으로 유사도를 다양하게 확인.
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

OUT = f"{ROOT}/prototype/voices/ab_v3more"
os.makedirs(OUT, exist_ok=True)

SENTENCES = {
    "calm": ("Today, let us open our hearts to the word of God "
             "and examine where we truly stand before Him."),
    "passionate": ("Do not harden your heart any longer! "
                   "Today is the day of salvation. "
                   "Turn back to the Lord while there is still time!"),
    "comfort": ("God sees your tears. He has not forgotten you, "
                "and His love for you never fails, even in your darkest hour."),
}
VS = VoiceSettings(stability=1.0, similarity_boost=1.0, use_speaker_boost=True, speed=0.8)


def save(pcm, p):
    with wave.open(p, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(24000)
        w.writeframes(pcm)


for name, text in SENTENCES.items():
    pcm = b"".join(client.text_to_speech.convert(
        voice_id=vid, text=text, model_id="eleven_v3",
        output_format="pcm_24000", language_code="en", voice_settings=VS))
    save(pcm, f"{OUT}/chae_{name}.wav")
    print(f"{name:11}: {len(pcm)/2/24000:.1f}s")

print("결과:", OUT)

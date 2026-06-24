"""긴 문장(~15초) 유사도 비교 — v3 vs multilingual_v2, 같은 문장으로.

격정적 톤은 인도 억양을 키워서 제외. 차분/강해/위로 톤만.
v3: stab=1.0(Robust)+sim=1.0+speaker_boost / v2: stab=0.5+sim=1.0+speaker_boost. speed 0.8 공통.
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

OUT = f"{ROOT}/prototype/voices/ab_v3plain"
os.makedirs(OUT, exist_ok=True)

SENTENCES = {
    "s1": ("The book of Romans was written by the apostle Paul to the believers in the city of Rome. "
           "In this letter, he explains the foundation of the gospel and what it means to live by faith."),
    "s2": ("In the beginning, God created the heavens and the earth. "
           "He made the light and the darkness, the land and the sea, "
           "and everything that lives and breathes upon it."),
    "s3": ("Jesus traveled through the towns and villages, teaching in their synagogues "
           "and proclaiming the good news of the kingdom, and healing every disease among the people."),
}
CONFIGS = [
    ("v3", "eleven_v3", VoiceSettings(stability=1.0, similarity_boost=1.0,
                                      use_speaker_boost=True, speed=0.8)),
    ("v2", "eleven_multilingual_v2", VoiceSettings(stability=0.5, similarity_boost=1.0,
                                                   use_speaker_boost=True, speed=0.8)),
]


def save(pcm, p):
    with wave.open(p, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(24000)
        w.writeframes(pcm)


for sname, text in SENTENCES.items():
    for mname, model, vs in CONFIGS:
        pcm = b"".join(client.text_to_speech.convert(
            voice_id=vid, text=text, model_id=model,
            output_format="pcm_24000", language_code="en", voice_settings=vs))
        save(pcm, f"{OUT}/chae_{sname}_{mname}.wav")
        print(f"{sname:11} {mname}: {len(pcm)/2/24000:.1f}s")

print("결과:", OUT)

"""lee/kwon(+chae 대조) 유사도 재평가 — 확정 설정으로 15초+ 긴 문장.

확정: eleven_multilingual_v2, stability=0.5, similarity_boost=1.0, speaker_boost, speed=0.8.
평이한 서술 문장(격정/감탄 없음)으로 순수 음색·억양 판단.
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

OUT = f"{ROOT}/prototype/voices/ab_alt"
os.makedirs(OUT, exist_ok=True)

SENTENCES = {
    "s1": ("The apostle Paul wrote his letter to the believers in Rome while he was staying "
           "in the city of Corinth. In this letter, he carefully explains the foundation of the "
           "Christian faith, showing how a person is made right with God not by their own efforts, "
           "but through faith in Jesus Christ alone."),
    "s2": ("In the beginning, God created the heavens and the earth. The earth was formless and "
           "empty, and darkness was over the surface of the deep. And God said, let there be light, "
           "and there was light. God saw that the light was good, and He separated the light "
           "from the darkness."),
}
VS = VoiceSettings(stability=0.5, similarity_boost=1.0, use_speaker_boost=True, speed=0.8)


def save(pcm, p):
    with wave.open(p, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(24000)
        w.writeframes(pcm)


for key in ["lee", "lee_alt", "kwon", "kwon_alt"]:
    vid = voices[key]["voice_id"]
    for sname, text in SENTENCES.items():
        pcm = b"".join(client.text_to_speech.convert(
            voice_id=vid, text=text, model_id="eleven_multilingual_v2",
            output_format="pcm_24000", language_code="en", voice_settings=VS))
        save(pcm, f"{OUT}/{key}_{sname}.wav")
        print(f"{key:5} {sname}: {len(pcm)/2/24000:.1f}s")

print("결과:", OUT)

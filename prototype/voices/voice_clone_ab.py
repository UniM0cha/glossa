"""Phase B — 번역 음성을 목사님 음색으로 바꾸는 두 접근 A/B 비교.

입력: prototype/out_en.wav (Gemini 번역 영어 음성, 24k PCM16) + 그 전사 텍스트.
- 접근 A (STS): out_en.wav 음성을 eleven_multilingual_sts_v2 로 음색만 목사님으로 변환.
- 접근 B (TTS): 같은 전사 텍스트를 eleven_flash_v2_5 로 목사님 보이스 재합성.
세 분(chae/lee/kwon) 각각 생성 → prototype/voices/ab/*.wav. 지연·크레딧 측정.
출력 포맷은 둘 다 pcm_24000(폰 재생 경로와 동일).
"""
import json
import os
import time
import wave

from dotenv import load_dotenv
from elevenlabs import ElevenLabs

ROOT = "/Users/solstice/Desktop/Toys/obs-live-interpreter"
load_dotenv(f"{ROOT}/server/.env")
client = ElevenLabs(api_key=os.environ["ELEVENLABS_API_KEY"])
voices = json.load(open(f"{ROOT}/prototype/voices/voices.json"))

SRC = f"{ROOT}/prototype/out_en.wav"
TEXT = ("The scripture we're sharing today is John 3:16. "
        "For God so loved the world that He gave His only begotten Son, "
        "that whoever believes in Him shall not perish.")
OUT = f"{ROOT}/prototype/voices/ab"
os.makedirs(OUT, exist_ok=True)
audio = open(SRC, "rb").read()


def save(pcm, path):
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(24000)
        w.writeframes(pcm)


def dur(pcm):
    return len(pcm) / 2 / 24000


def credits():
    return client.user.subscription.get().character_count


c0 = credits()
print(f"시작 크레딧 사용량: {c0}\n")
print(f"{'voice':6} {'접근':9} {'지연':>6} {'출력길이':>8}")
print("-" * 36)

for key, info in voices.items():
    vid = info["voice_id"]
    # 접근 A — STS (음색 변환): 입력 음성의 운율 유지, 음색만 교체
    t = time.time()
    pcm = b"".join(client.speech_to_speech.convert(
        voice_id=vid, audio=audio, model_id="eleven_multilingual_sts_v2",
        output_format="pcm_24000", file_format="other"))
    save(pcm, f"{OUT}/{key}_A_sts.wav")
    print(f"{key:6} {'A:STS':9} {time.time()-t:5.1f}s {dur(pcm):7.1f}s")

    # 접근 B — TTS (재합성): 텍스트에서 목사님 보이스로 새로 합성
    t = time.time()
    pcm = b"".join(client.text_to_speech.convert(
        voice_id=vid, text=TEXT, model_id="eleven_flash_v2_5",
        output_format="pcm_24000", language_code="en"))
    save(pcm, f"{OUT}/{key}_B_tts.wav")
    print(f"{key:6} {'B:TTS':9} {time.time()-t:5.1f}s {dur(pcm):7.1f}s")

c1 = credits()
print(f"\n끝 크레딧 사용량: {c1}  (이번 실행 총 {c1-c0} 크레딧 소모)")
print(f"결과 wav: {OUT}/   (*_A_sts.wav=음색변환, *_B_tts.wav=재합성)")

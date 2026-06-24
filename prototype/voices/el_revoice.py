"""lee/kwon 다른 구간으로 IVC 재생성 — 기존과 비교용 (lee_alt / kwon_alt).

segments/{key}_alt.mp3 (다른 설교 구간) → 새 IVC → voices.json 에 추가.
"""
import json
import os

from dotenv import load_dotenv
from elevenlabs import ElevenLabs

ROOT = "/Users/solstice/Desktop/Toys/obs-live-interpreter"
load_dotenv(f"{ROOT}/server/.env")
client = ElevenLabs(api_key=os.environ["ELEVENLABS_API_KEY"])
OUT = f"{ROOT}/prototype/voices/voices.json"
voices = json.load(open(OUT))

NEW = {
    "lee_alt": ("길튼-이호균-alt", f"{ROOT}/prototype/voices/segments/lee_alt.mp3"),
    "kwon_alt": ("길튼-권순호-alt", f"{ROOT}/prototype/voices/segments/kwon_alt.mp3"),
}

for key, (name, path) in NEW.items():
    try:
        with open(path, "rb") as f:
            v = client.voices.ivc.create(name=name, description="다른 설교 구간 재학습", files=[f])
        voices[key] = {"voice_id": v.voice_id, "name": name}
        print(f"{key} → {v.voice_id}")
    except Exception as e:
        print(f"{key}: ERR {type(e).__name__} {getattr(e, 'body', repr(e))}"[:200])

json.dump(voices, open(OUT, "w"), ensure_ascii=False, indent=2)
print("saved voices.json")

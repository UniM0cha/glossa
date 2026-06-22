"""설교 음원으로 ElevenLabs Instant Voice Clone 생성 → voices.json 에 voice_id 저장.

usage: python el_create_voice.py [chae lee kwon ...]   # 인자 없으면 전체
입력: segments/<key>_sermon.mp3  (없으면 skip)
"""
import json
import os
import sys

from dotenv import load_dotenv
from elevenlabs import ElevenLabs

ROOT = "/Users/solstice/Desktop/Toys/obs-live-interpreter"
load_dotenv(f"{ROOT}/server/.env.local")
client = ElevenLabs(api_key=os.environ["ELEVENLABS_API_KEY"])

SPEAKERS = {
    "chae": ("길튼-채성렬", "길튼교회 채성렬 목사 설교 음성"),
    "lee": ("길튼-이호균", "길튼교회 이호균 목사 설교 음성"),
    "kwon": ("길튼-권순호", "길튼교회 권순호 목사 설교 음성"),
}
SEG = f"{ROOT}/prototype/voices/segments"
OUT = f"{ROOT}/prototype/voices/voices.json"
voices = json.load(open(OUT)) if os.path.exists(OUT) else {}

for key in (sys.argv[1:] or list(SPEAKERS)):
    name, desc = SPEAKERS[key]
    path = f"{SEG}/{key}_sermon.mp3"
    if not os.path.exists(path):
        print(f"skip {key}: {path} 없음")
        continue
    mb = os.path.getsize(path) / 1e6
    print(f"IVC {key} ({mb:.1f}MB) …", flush=True)
    try:
        with open(path, "rb") as fh:
            v = client.voices.ivc.create(name=name, description=desc, files=[fh])
        voices[key] = {"voice_id": v.voice_id, "name": name}
        print(f"  → voice_id={v.voice_id}")
    except Exception as e:
        print(f"  ERR: {type(e).__name__} status={getattr(e, 'status_code', None)} "
              f"body={getattr(e, 'body', None)}")

json.dump(voices, open(OUT, "w"), ensure_ascii=False, indent=2)
print("saved:", OUT)
print(json.dumps(voices, ensure_ascii=False, indent=2))

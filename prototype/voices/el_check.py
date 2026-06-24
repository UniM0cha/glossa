"""ElevenLabs API 키 유효성 + 구독 tier 확인 (Phase A/B 착수 전 헬스체크)."""
import os
from dotenv import load_dotenv
from elevenlabs import ElevenLabs

ROOT = "/Users/solstice/Desktop/Toys/glossa"
load_dotenv(f"{ROOT}/server/.env")
key = os.environ.get("ELEVENLABS_API_KEY", "")
print("key set:", bool(key))
c = ElevenLabs(api_key=key)

# 구독/사용량 (SDK 2.53 메서드 후보 두 가지 시도)
for attempt in ("user.subscription.get", "user.get"):
    try:
        s = c.user.subscription.get() if attempt == "user.subscription.get" else c.user.get()
        tier = getattr(s, "tier", None) or getattr(getattr(s, "subscription", None), "tier", "?")
        cc = getattr(s, "character_count", "?")
        cl = getattr(s, "character_limit", "?")
        print(f"{attempt} OK | tier={tier} used={cc}/{cl}")
        break
    except Exception as e:
        print(f"{attempt} err: {repr(e)[:160]}")

try:
    vs = c.voices.search()
    print("voices count:", len(vs.voices))
except Exception as e:
    print("voices err:", repr(e)[:160])

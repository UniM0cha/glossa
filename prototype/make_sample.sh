#!/usr/bin/env bash
# 한국어 설교 샘플 WAV(16kHz mono 16-bit) 생성 — macOS 내장 say + afconvert만 사용.
# 외부 의존성(ffmpeg 등) 없이 반복 가능한 테스트 입력을 만든다.
#
#   ./make_sample.sh                 # 기본 설교 문구
#   ./make_sample.sh "원하는 문장"   # 직접 문구 지정
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p samples

TEXT=${1:-"오늘 우리가 함께 나눌 말씀은 요한복음 삼장 십육절입니다. 하나님이 세상을 이처럼 사랑하사 독생자를 주셨으니, 누구든지 그를 믿으면 멸망하지 않고 영생을 얻게 하려 하심이라."}

# 설치된 한국어(ko_KR) 음성 자동 탐색.
# `say -v '?'` 에서 locale 토큰(ko_KR)을 기준으로 그 앞의 음성 이름 전체를 뽑는다.
# (멀티링구얼 음성은 이름에 공백이 있음: "Eddy (한국어(한국))" → $1만 떼면 영어 Eddy가 잡혀 한국어를 못 읽음)
KO_VOICES=$(say -v '?' | sed -E 's/  +#.*//' \
  | awk '{for(i=1;i<=NF;i++) if($i ~ /^[a-z][a-z]_[A-Z][A-Z]$/){loc=$i; name=""; for(j=1;j<i;j++) name=name (j>1?" ":"") $j; if(loc=="ko_KR") print name}}')
if [ -z "${KO_VOICES}" ]; then
  echo "한국어 음성(ko_KR)이 설치돼 있지 않습니다." >&2
  echo "시스템 설정 > 손쉬운 사용 > 음성 콘텐츠 > 시스템 음성에서 한국어(예: Yuna)를 추가한 뒤 다시 실행하세요." >&2
  echo "또는 영어 등 다른 16kHz mono WAV 를 직접 준비해 milestone_a.py -i 로 넘겨도 됩니다." >&2
  exit 1
fi
# 단일 토큰 고품질 음성 Yuna 를 우선, 없으면 첫 ko_KR 음성
if printf '%s\n' "$KO_VOICES" | grep -qx "Yuna"; then
  VOICE="Yuna"
else
  VOICE=$(printf '%s\n' "$KO_VOICES" | head -1)
fi
echo "사용 음성: $VOICE"

say -v "$VOICE" -o samples/_tmp.aiff "$TEXT"
# LEI16@16000 = little-endian int16, 16kHz / -c 1 = mono / -f WAVE
afconvert -f WAVE -d LEI16@16000 -c 1 samples/_tmp.aiff samples/sermon_ko_16k.wav
rm -f samples/_tmp.aiff

echo "생성됨: prototype/samples/sermon_ko_16k.wav (16kHz mono 16-bit PCM)"

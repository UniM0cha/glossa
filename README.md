# OBS Live Interpreter (교회 실시간 설교 통역)

> 🚧 **진행 중 (Work in Progress)** — 아직 설계/검증 단계이며 동작하는 코드는 없습니다.
> 현재는 README·CLAUDE.md 등 문서만 있는 상태이고, 아래 로드맵의 Phase 0부터 시작합니다.

한국어 설교를 **실시간으로 외국어 음성으로 통역**하여, 외국인 성도가 무선 이어폰으로
자신의 언어로 들을 수 있게 하는 OBS Studio 플러그인 프로젝트입니다.

> 프로젝트 이름은 임시입니다. 원하시면 `church-live-translation` 등으로 바꿔도 됩니다.

---

## 1. 무엇을 만들려는가

- 예배 중 송출(OBS)되는 **설교 음성(한국어)** 을 가로채(tap) 복사합니다.
- 복사한 음성을 **Google Gemini Live API의 실시간 음성→음성 번역**에 흘려보냅니다.
- 번역되어 돌아온 **외국어 음성**을 OBS 송출 PC에 연결된 **이어폰(무선/유선)** 으로 재생합니다.
- 방송으로 나가는 원본(한국어)은 **절대 건드리지 않습니다.** 통역은 옆길(side-channel)로만 흐릅니다.

```
[설교 마이크/믹서]
       │ (48kHz PCM, OBS 내부)
       ▼
┌──────────────────────────────────────────────┐
│ OBS 오디오 소스                                │
│   └─ [Live Interpreter 필터]                   │
│         ├─ 원본 그대로 통과 ───────────────► OBS 송출/녹화 (한국어 유지)
│         └─ 복사본 tap                          │
└─────────────────┼────────────────────────────┘
                  │ 48kHz → 16kHz mono 리샘플, 100ms 청크
                  ▼
        [Gemini Live Translate API]  (WebSocket, audio-in / audio-out)
                  │ 24kHz mono PCM (번역된 외국어 음성)
                  ▼
        [출력 장치 = 이어폰]  (CoreAudio / miniaudio)
```

---

## 2. 핵심 기술 사실 (1차 출처 검증, 2026-06-20 기준)

> ⚠️ Gemini 번역 모델은 **preview** 상태입니다. 모델 ID·요금·포맷은 바뀔 수 있으니
> **구현 직전에 반드시 공식 문서로 다시 확인**하세요. (자세한 검증 규칙은 `CLAUDE.md` 참고)

### Gemini Live API — 실시간 번역
- **모델 ID**: `gemini-3.5-live-translate-preview` (preview)
- **동작 방식**: STT→번역→TTS로 쪼개지 않고, **오디오 입력 → 오디오 출력**을 한 모델이 end-to-end로 처리. 억양·속도·피치를 보존.
- **입력 오디오**: Raw 16-bit PCM, **16kHz**, mono, little-endian (권장 청크 ~100ms)
- **출력 오디오**: Raw 16-bit PCM, **24kHz**, mono, little-endian
- **언어 지정**: BCP-47 코드. `targetLanguageCode`(예: `"en"`, `"vi"`, `"zh"`)로 목표 언어 지정.
  `echoTargetLanguage`(boolean)로 "이미 목표 언어인 입력"을 따라 말할지/침묵할지 제어.
- **제약**: 이 번역 모드는 **tools / system instruction 미지원** — 순수 음성 번역만.
- **지원 언어**: 70개 이상 자동 감지.
- **접속 방식**:
  - SDK: Python `google-genai`(`from google import genai`), JS `@google/genai`
  - 또는 WebSocket 직접:
    `wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent`
- **키 보안**: 클라이언트 배포 시 **ephemeral token**(현재 `v1alpha`) 권장. API 키 직접 노출 금지.

### OBS 플러그인 — 오디오 필터
- 필터는 `OBS_SOURCE_TYPE_FILTER` 타입의 source이며, 부모 source에 붙어 그 출력을 가로챕니다.
- 콜백: `obs_source_info.filter_audio(void *data, struct obs_audio_data *audio)`
  - 받은 `obs_audio_data`(PCM 샘플)를 **그대로 반환**하여 방송 음성은 변형하지 않습니다.
  - 반환 직전에 샘플을 **복사**해 옆길 큐로 넘깁니다 (tap).
  - 무거운 작업(네트워크/리샘플)은 필터 콜백 안에서 하지 말고 **별도 워커 스레드**에서 처리(오디오 콜백 블로킹 금지).
- 참고 구현: 비동기 오디오 필터 패턴 `norihiro/obs-async-audio-filter`.

---

## 3. 아키텍처 불변 규칙 (반드시 지킬 것)

1. **원본 불변**: `filter_audio`는 입력 PCM을 변형/치환하지 않고 그대로 통과시킨다. 통역 음성이 OBS 믹스/녹화/송출로 새어 들어가면 안 된다.
2. **피드백 차단**: 통역 출력(이어폰)이 다시 설교 마이크/OBS 입력으로 들어가 루프를 만들지 않게 한다. 출력은 전용 장치로만.
3. **오디오 콜백 비블로킹**: 리샘플·base64·WebSocket 전송·재생은 워커 스레드에서. 필터 콜백은 복사 후 즉시 반환.
4. **포맷 변환 명시**: OBS 내부(보통 48kHz float) → Gemini 입력(16kHz 16-bit mono) 리샘플. 출력은 24kHz로 받아 장치 샘플레이트에 맞춤.
5. **키는 커밋 금지**: API 키/토큰은 환경변수·설정 파일·OS 키체인으로. 절대 소스에 하드코딩하지 않는다.

---

## 4. 단계별 로드맵

### Phase 0 — 파이프라인 검증 (OBS 없이, 가장 먼저)
OBS C++에 투자하기 전에 **핵심 가설(지연시간·품질·비용)** 부터 증명합니다.
- macOS에 가상 오디오 장치(예: **BlackHole**) 설치 → 시스템/설교 음성을 그쪽으로 라우팅.
- 작은 **Python 프로토타입**: `sounddevice`로 BlackHole 캡처 → `google-genai`로 번역 스트림 → 이어폰으로 재생.
- 측정: 체감 지연, 통역 자연스러움, 1~2시간 예배 기준 **API 비용**, 네트워크 끊김 시 동작.
- 위치(예정): `prototype/`

### Phase 1 — 실제 OBS 플러그인 (단일 언어)
- C++ + libobs, CMake(OBS 플러그인 템플릿) 기반.
- tap 오디오 필터 + 워커 스레드 + WebSocket 클라이언트 + 출력 장치 재생.
- 설정 UI: 목표 언어, 출력 장치 선택, API 키.
- 위치(예정): `src/`

### Phase 2 — 다국어 / 다수 청취자
> 현재 설계는 "OBS PC에 연결된 이어폰 1개 = 1개 언어"로, **한 명/한 언어**만 듣습니다.
> 여러 외국인이 각자 다른 언어로 들으려면 분배 방식이 필요합니다.
- 옵션 A: 플러그인이 로컬 웹서버를 띄우고, 성도들이 휴대폰으로 접속해 언어를 골라 스트림 수신(WebRTC/HLS).
- 옵션 B: 언어별 다중 Gemini 세션 + 다중 출력.
- 재접속/장애 복구, 비용 가드레일, 운영자용 모니터링.

---

## 5. 알아둘 제약 / 리스크

- **지연시간**: "sub-second"라 해도 음성→음성 통역은 구문 단위로 약간의 지연이 생깁니다. 실시간 동시통역 수준의 기대치는 사전에 맞춰두세요.
- **비용**: Live API는 오디오 시간 기준 과금. 긴 예배에서 누적될 수 있으니 설교 구간에만 켜고 비용을 모니터링하세요.
- **네트워크 의존**: 예배 중 안정적 인터넷 필수. 끊김 시 재접속·무음 처리 로직 필요.
- **preview 모델**: 모델 ID/스펙이 예고 없이 바뀔 수 있음 — `CLAUDE.md`의 검증 규칙 준수.
- **프라이버시**: 설교 음성이 Google 클라우드로 전송됨. 필요하면 교회 측에 고지/동의를 고려.

---

## 6. 디렉토리 구조 (예정)

```
obs-live-interpreter/
├── README.md          # 이 문서
├── CLAUDE.md          # Claude Code 작업 지침 / 검증 규칙
├── .gitignore
├── prototype/         # Phase 0: Python 파이프라인 검증
├── src/               # Phase 1: C++ OBS 플러그인
└── docs/              # 설계 메모, 운영 가이드
```

---

## 7. 참고 링크

**Gemini Live API / 번역**
- [Live translation with Gemini Live API — Google AI for Developers](https://ai.google.dev/gemini-api/docs/live-api/live-translate)
- [Live API capabilities guide](https://ai.google.dev/gemini-api/docs/live-api/capabilities)
- [Gemini Live API overview](https://ai.google.dev/gemini-api/docs/live-api)
- [Fluid, natural voice translation with Gemini 3.5 Live Translate (Google blog)](https://blog.google/innovation-and-ai/models-and-research/gemini-models/gemini-live-3-5-translate/)
- [Building a Real-Time Audio Translator with Gemini Live API (Kaz Sato, Google Cloud)](https://medium.com/google-cloud/building-a-real-time-audio-translator-with-gemini-live-api-03fb881b1774)

**OBS 플러그인**
- [OBS Plugins docs](https://docs.obsproject.com/plugins)
- [Source API Reference (obs_source_t)](https://docs.obsproject.com/reference-sources)
- [obs-async-audio-filter (비동기 오디오 필터 참고 구현)](https://github.com/norihiro/obs-async-audio-filter)

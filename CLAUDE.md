# CLAUDE.md — OBS Live Interpreter

이 저장소에서 작업할 때 따르는 지침입니다. 전역 `~/CLAUDE.md` 규칙도 함께 적용됩니다.

## 언어 / 커뮤니케이션
- 항상 **존댓말(해요체/합쇼체)**. 사용자가 반말을 써도 반말하지 않습니다.
- 문서·주석은 한국어, 코드 식별자·기술 용어는 원어 그대로.

## 프로젝트 한 줄 요약
한국어 설교를 Gemini Live 번역으로 실시간 외국어 음성으로 바꿔, OBS 송출 PC의 이어폰으로
들려주는 **OBS 오디오 필터 플러그인**. 자세한 배경·로드맵은 `README.md` 참고.

## 절대 어기면 안 되는 아키텍처 불변 규칙
1. **방송 원본 불변**: `filter_audio` 콜백은 입력 PCM을 변형/치환하지 않고 **그대로 반환**한다.
   통역 음성이 OBS 송출/녹화 믹스로 절대 들어가면 안 된다. (필터는 복사만 하는 *tap*.)
2. **피드백 루프 차단**: 통역 출력(이어폰)이 설교 마이크/OBS 입력으로 되돌아가지 않게 한다.
3. **오디오 콜백 비블로킹**: 리샘플/네트워크/재생은 워커 스레드에서. 콜백은 복사 후 즉시 반환.
4. **키는 커밋 금지**: API 키·ephemeral token은 env/설정/키체인으로만. 소스·로그·커밋에 남기지 않는다.

## 빠르게 변하는 LLM 사양 — 검증 규칙 (중요)
Gemini 번역 모델은 **preview**라 자주 바뀝니다. **추측으로 단정하지 말 것.**
- 모델 ID·요금·오디오 포맷·파라미터를 코드/문서에 박기 전, **공식 1차 출처**
  (ai.google.dev, blog.google, cloud.google.com 공식 문서)로 **재확인**한다.
- 2차 매체(SEO 블로그)나 기억에만 의존해 모델명을 인용하지 않는다. (`llm-hardware-spec-verification` 스킬 정신 준수.)
- 아래 "검증된 사실"에 적힌 값도 날짜가 지났으면 다시 확인하고, 바뀌면 이 파일과 `README.md`를 함께 갱신한다.

### 검증된 사실 (2026-06-20, 출처 확인 완료)
- 모델: `gemini-3.5-live-translate-preview` (preview)
- 입력 오디오: 16-bit PCM, 16kHz, mono, little-endian, 권장 청크 ~100ms
- 출력 오디오: 16-bit PCM, 24kHz, mono, little-endian
- 언어: BCP-47 코드, `targetLanguageCode`로 목표 언어, `echoTargetLanguage`(bool)
- 번역 모드는 **tools / system instruction 미지원** (순수 음성 번역)
- WebSocket: `wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent`
- SDK: Python `google-genai`, JS `@google/genai`
- 출처: https://ai.google.dev/gemini-api/docs/live-api/live-translate

## OBS 기술 메모
- 오디오 필터 = `OBS_SOURCE_TYPE_FILTER`, 콜백 `obs_source_info.filter_audio(data, obs_audio_data*)`.
- OBS 내부 오디오는 보통 48kHz float planar → Gemini 입력(16kHz 16-bit mono)으로 리샘플 필요.
- 빌드: C++ / libobs / CMake (OBS 플러그인 템플릿). 대상 OS는 macOS(개발 머신 darwin) 우선.
- 비동기 처리 참고: `github.com/norihiro/obs-async-audio-filter`.

## 작업 순서 권장
- 먼저 **Phase 0(`prototype/`, Python)** 로 지연/품질/비용을 검증한 뒤 C++ 플러그인에 착수한다.
  (핵심 리스크를 OBS 빌드 복잡도 없이 먼저 제거.)

## 빌드 / 실행 / 테스트
- (아직 코드 없음. 코드가 생기면 여기에 실제 빌드·실행 명령을 적는다.)
- 명령을 추가할 때는 추측이 아니라 실제로 돌려본 명령만 기록한다.

## 서브에이전트
- 서브에이전트(Task/Agent, 워크플로 포함)에 **Haiku 모델 사용 금지** (환각 심함). 미지정 시 부모 모델 상속 유지, Sonnet 이상만 명시.

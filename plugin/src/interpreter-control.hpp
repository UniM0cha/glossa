#pragma once
/*
 * 통역 필터 외부 컨트롤 API — 도크(Qt)·핫키가 공유한다.
 * 구현은 plugin-main.cpp (등록된 필터 인스턴스 전역 레지스트리 위에서 동작).
 */

#ifdef __cplusplus
extern "C" {
#endif

enum interpreter_state_t {
	INTERP_NONE = 0,   /* 등록된 통역 필터 없음 */
	INTERP_OFF,        /* 모두 OFF */
	INTERP_CONNECTING, /* ON 이지만 서버 미연결 (시도 중) */
	INTERP_LIVE,       /* ON + 서버 연결됨 */
	INTERP_ERROR,      /* ON 이지만 연결 실패 — 인증/네트워크 (사유는 connection_error()) */
};

/* 등록된 모든 통역 필터의 집계 상태 */
int interpreter_state(void);

/* 전체 토글: 하나라도 ON이면 전부 OFF, 아니면 전부 ON */
void interpreter_toggle_all(void);

#ifdef __cplusplus
}
#endif

/*
OBS Live Interpreter — 오디오 tap 필터 (M1.0)
Copyright (C) 2026 Jeongyun Lee

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version. (libobs 링크로 GPL)

이 파일은 M1.0 단계: OBS 오디오 필터를 등록하고, filter_audio 콜백에서
입력 PCM 을 "변형 없이 그대로 통과(tap)"시키며 프레임 수만 집계/로그한다.
복사 → 48k→16k 리샘플 → WSS 업링크는 M1.1 에서 추가한다.
*/
#include <obs-module.h>
#include <plugin-support.h>

OBS_DECLARE_MODULE()
OBS_MODULE_USE_DEFAULT_LOCALE(PLUGIN_NAME, "en-US")

/* 필터 인스턴스 상태 (M1.0: 통계만) */
struct interpreter_filter {
	obs_source_t *context;
	uint64_t call_count;
	uint64_t frame_count;
};

static const char *interpreter_filter_get_name(void *unused)
{
	UNUSED_PARAMETER(unused);
	return obs_module_text("InterpreterFilter");
}

static void *interpreter_filter_create(obs_data_t *settings, obs_source_t *source)
{
	UNUSED_PARAMETER(settings);
	struct interpreter_filter *f = bzalloc(sizeof(struct interpreter_filter));
	f->context = source;
	obs_log(LOG_INFO, "[interpreter] 필터 생성됨");
	return f;
}

static void interpreter_filter_destroy(void *data)
{
	struct interpreter_filter *f = data;
	obs_log(LOG_INFO, "[interpreter] 필터 제거 (누적 %llu 콜백, %llu 프레임 tap)",
		(unsigned long long)f->call_count, (unsigned long long)f->frame_count);
	bfree(f);
}

/*
 * tap: 입력 PCM 을 변형/치환 없이 그대로 반환한다.
 * → 방송 송출/녹화 믹스에 통역 음성이 절대 섞이지 않는다 (아키텍처 불변규칙 #1).
 * M1.0 에서는 프레임 수만 집계/로그. (복사→리샘플→업링크는 M1.1)
 */
static struct obs_audio_data *interpreter_filter_audio(void *data, struct obs_audio_data *audio)
{
	struct interpreter_filter *f = data;
	f->call_count++;
	f->frame_count += audio->frames;
	/* 로그 폭주 방지: 200콜백마다 한 번 (~수 초 간격) */
	if (f->call_count % 200 == 0)
		obs_log(LOG_INFO, "[interpreter] tap %llu 콜백 / %llu 프레임 (직전 %u frames)",
			(unsigned long long)f->call_count, (unsigned long long)f->frame_count, audio->frames);
	return audio; /* 원본 그대로 통과 */
}

static struct obs_source_info interpreter_filter_info = {
	.id = "obs_live_interpreter_filter",
	.type = OBS_SOURCE_TYPE_FILTER,
	.output_flags = OBS_SOURCE_AUDIO,
	.get_name = interpreter_filter_get_name,
	.create = interpreter_filter_create,
	.destroy = interpreter_filter_destroy,
	.filter_audio = interpreter_filter_audio,
};

bool obs_module_load(void)
{
	obs_register_source(&interpreter_filter_info);
	obs_log(LOG_INFO, "OBS Live Interpreter 로드됨 (버전 %s)", PLUGIN_VERSION);
	return true;
}

void obs_module_unload(void)
{
	obs_log(LOG_INFO, "OBS Live Interpreter 언로드됨");
}

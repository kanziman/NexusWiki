-- 0011_workspace_byok_api_key.sql
-- 워크스페이스 BYOK (사용자 커스텀 OpenRouter/OpenAI API 키) 저장 컬럼 추가

alter table public.workspaces
  add column if not exists custom_api_key text check (custom_api_key is null or char_length(btrim(custom_api_key)) <= 500);

comment on column public.workspaces.custom_api_key is
  '사용자 개인 OpenRouter/OpenAI API 키 (BYOK). 등록 시 월간 크레딧 차감 없이 무제한으로 AI 질의 및 소스 분석을 수행한다.';

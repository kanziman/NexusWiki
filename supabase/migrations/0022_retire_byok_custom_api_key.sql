-- 0022_retire_byok_custom_api_key.sql
-- BYOK(개인 API 키) 기능 비활성화 — 워커가 custom_api_key를 읽은 적이 없어
-- 등록해도 실제로는 아무 효과가 없었다. 더 이상 쓰이지 않는 외부 비밀키를
-- DB에 방치하지 않기 위해 기존 값을 비운다. 컬럼 자체는 남겨둔다.

update public.workspaces
  set custom_api_key = null
  where custom_api_key is not null;

comment on column public.workspaces.custom_api_key is
  'BYOK는 UI·실제 라우팅 모두 비활성 상태 — 워커가 읽지 않는다. 재도입 전까지 값을 쓰지 않는다.';

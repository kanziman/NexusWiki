-- =============================================================================
-- NexusWiki 0015: 워크스페이스 슬러그 정본
--
-- 관련 태스크: #14
-- 소비자:       Google OAuth 워크스페이스 생성, 향후 내부·공개 URL 경로
-- =============================================================================

alter table public.workspaces add column slug text;

-- 기존 행은 id에서 결정적으로 만들면 제목 정규화 규칙이나 실행 순서에 의존하지 않고
-- 충돌하지 않는다. 이후 생성 경로는 애플리케이션에서 전역 충돌을 해소한다.
update public.workspaces
set slug = 'ws-' || left(id::text, 8)
where slug is null;

alter table public.workspaces
  alter column slug set not null,
  add constraint workspaces_slug_key unique (slug),
  add constraint workspaces_slug_format check (
    slug ~ '^[0-9a-z가-힣][0-9a-z가-힣-]*$'
    and char_length(slug) between 1 and 80
  );

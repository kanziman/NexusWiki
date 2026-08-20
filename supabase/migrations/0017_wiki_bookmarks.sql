-- =============================================================================
-- NexusWiki 0017: 위키 문서 즐겨찾기
--
-- 관련 태스크: checklists_v2.json > phases.v2_phase_6.UX-02
-- 근거:       docs/design-systems/v2/workspace-home-prd.md §4.1 옵션 2
-- =============================================================================

-- -----------------------------------------------------------------------------
-- user_wiki_bookmarks: 사용자별 위키 문서 즐겨찾기
-- -----------------------------------------------------------------------------

create table public.user_wiki_bookmarks (
  user_id      uuid not null references auth.users (id) on delete cascade,
  wiki_id      uuid not null,
  workspace_id uuid not null,
  created_at   timestamptz not null default now(),

  primary key (user_id, wiki_id),

  -- 복합 FK로 wiki_id가 항상 자신이 속한 workspace_id와 일치하도록 강제한다
  -- (wiki_page_publications_tenant_fkey와 동일 패턴) — 이게 없으면 응용
  -- 코드가 실수로 다른 워크스페이스의 wiki_id와 workspace_id를 잘못 짝지어
  -- 넣어도 DB가 막지 못한다.
  constraint user_wiki_bookmarks_tenant_fkey
    foreign key (wiki_id, workspace_id)
    references public.wiki_pages (id, workspace_id) on delete cascade
);

alter table public.user_wiki_bookmarks enable row level security;

-- LNB 즐겨찾기 목록·필터 조회용 (workspace_id, created_at desc)
create index user_wiki_bookmarks_user_workspace_idx
  on public.user_wiki_bookmarks (user_id, workspace_id, created_at desc);

-- RLS 정책: user_wiki_bookmarks
-- 워크스페이스 멤버십이 아니라 소유자 본인만 자기 즐겨찾기를 본다 —
-- 팀원이라도 다른 사람이 뭘 즐겨찾기했는지는 사적인 정보다.
create policy user_wiki_bookmarks_select_own
  on public.user_wiki_bookmarks
  for select to authenticated
  using (user_id = (select auth.uid()));

create policy user_wiki_bookmarks_insert_own
  on public.user_wiki_bookmarks
  for insert to authenticated
  with check (
    user_id = (select auth.uid())
    and public.is_workspace_member(workspace_id)
  );

create policy user_wiki_bookmarks_delete_own
  on public.user_wiki_bookmarks
  for delete to authenticated
  using (user_id = (select auth.uid()));

grant select, insert, delete on table public.user_wiki_bookmarks to authenticated;

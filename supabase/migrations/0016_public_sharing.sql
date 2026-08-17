-- =============================================================================
-- NexusWiki 0016: 공개 위키 공유 및 1:1 사이드카
--
-- 관련 태스크: PUB-01
-- 불변 규칙:   PRODUCT-INVARIANTS.md §3 (검증 상태), §4 (공개 네임스페이스), §5 (사이드카)
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. workspace_public_settings: 워크스페이스 공개 설정 및 마스터 킬스위치
-- -----------------------------------------------------------------------------

create table public.workspace_public_settings (
  workspace_id         uuid primary key
                         references public.workspaces (id) on delete cascade,
  workspace_slug       text not null,
  allow_public_sharing boolean not null default false,
  public_display_name  text,
  public_description   text,
  updated_at           timestamptz not null default now(),
  constraint workspace_public_settings_slug_key unique (workspace_slug)
);

alter table public.workspace_public_settings enable row level security;

-- 슬러그 자동 파생 및 동기화 함수/트리거
create or replace function public.derive_workspace_public_slug()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  select w.slug into new.workspace_slug
  from public.workspaces w where w.id = new.workspace_id;
  return new;
end;
$$;

create trigger workspace_public_settings_derive_slug
  before insert or update on public.workspace_public_settings
  for each row execute function public.derive_workspace_public_slug();

create or replace function public.sync_workspace_public_slug()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  update public.workspace_public_settings
     set workspace_slug = new.slug, updated_at = now()
   where workspace_id = new.id;
  return new;
end;
$$;

create trigger workspaces_sync_public_slug
  after update of slug on public.workspaces
  for each row when (new.slug is distinct from old.slug)
  execute function public.sync_workspace_public_slug();

-- RLS 정책: workspace_public_settings
create policy workspace_public_settings_select_public
  on public.workspace_public_settings
  for select to anon, authenticated
  using (allow_public_sharing = true);

create policy workspace_public_settings_select_member
  on public.workspace_public_settings
  for select to authenticated
  using (public.is_workspace_member(workspace_id));

create policy workspace_public_settings_insert_owner
  on public.workspace_public_settings
  for insert to authenticated
  with check (public.has_workspace_role(workspace_id, 'owner'));

create policy workspace_public_settings_update_owner
  on public.workspace_public_settings
  for update to authenticated
  using (public.has_workspace_role(workspace_id, 'owner'))
  with check (public.has_workspace_role(workspace_id, 'owner'));

grant select on table public.workspace_public_settings to anon, authenticated;
grant insert, update on table public.workspace_public_settings to authenticated;

-- -----------------------------------------------------------------------------
-- 2. wiki_page_publications: 인간 승인 기반 위키 발행본
-- -----------------------------------------------------------------------------

create table public.wiki_page_publications (
  wiki_page_id        uuid primary key,
  workspace_id        uuid not null,
  published_slug      text not null,
  published_title     text not null,
  published_content   text not null,
  published_citations jsonb not null default '[]'::jsonb,
  published_at        timestamptz not null default now(),
  published_by        uuid not null references auth.users (id) on delete restrict,

  constraint wiki_page_publications_workspace_slug_key
    unique (workspace_id, published_slug),

  constraint wiki_page_publications_tenant_fkey
    foreign key (wiki_page_id, workspace_id)
    references public.wiki_pages (id, workspace_id) on delete cascade
);

alter table public.wiki_page_publications enable row level security;

-- 검증 게이트 트리거
create or replace function public.enforce_publication_verified()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  if not exists (
    select 1 from public.wiki_pages wp
    where wp.id = new.wiki_page_id
      and wp.workspace_id = new.workspace_id
      and wp.verification_status = 'verified'
  ) then
    raise exception '검증 완료된 문서만 공개할 수 있습니다'
      using errcode = '42501';
  end if;
  return new;
end;
$$;

create trigger wiki_page_publications_verify_gate
  before insert or update on public.wiki_page_publications
  for each row execute function public.enforce_publication_verified();

-- RLS 정책: wiki_page_publications
create policy wiki_page_publications_select_public
  on public.wiki_page_publications
  for select to anon, authenticated
  using (
    exists (
      select 1 from public.workspace_public_settings s
      where s.workspace_id = wiki_page_publications.workspace_id
        and s.allow_public_sharing = true
    )
  );

create policy wiki_page_publications_select_member
  on public.wiki_page_publications
  for select to authenticated
  using (public.is_workspace_member(workspace_id));

create policy wiki_page_publications_write_editor
  on public.wiki_page_publications
  for all to authenticated
  using (public.has_workspace_role(workspace_id, 'editor'))
  with check (public.has_workspace_role(workspace_id, 'editor'));

grant select on table public.wiki_page_publications to anon, authenticated;
grant insert, update, delete on table public.wiki_page_publications to authenticated;

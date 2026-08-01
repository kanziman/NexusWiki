-- =============================================================================
-- NexusWiki 0001: 코어 스키마
--
-- 관련 태스크: P1-DB-01
-- 설계 근거:  checklists.json > decisions.tenancy (team-first)
--             checklists.json > decisions.original_file_retention (Supabase Storage)
--             checklists.json > decisions.db_access (hybrid)
--
-- 이 마이그레이션은 테이블 생성과 함께 RLS를 "정책 없이" 활성화합니다.
-- 정책이 없는 RLS = 전면 거부이므로, 0004에서 정책을 붙이기 전까지
-- anon/authenticated 키로는 아무것도 읽거나 쓸 수 없습니다.
-- 테이블이 잠깐이라도 무방비로 노출되는 창을 만들지 않기 위함입니다.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 공통: updated_at 자동 갱신
-- -----------------------------------------------------------------------------
create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;


-- -----------------------------------------------------------------------------
-- 1. 워크스페이스 (멀티테넌시의 루트)
-- -----------------------------------------------------------------------------
create table public.workspaces (
  id         uuid primary key default gen_random_uuid(),
  name       text not null check (char_length(btrim(name)) between 1 and 100),
  kind       text not null default 'team' check (kind in ('personal', 'team')),
  -- on delete restrict: 워크스페이스를 소유한 사용자는 삭제 전에
  -- 소유권을 이전해야 합니다. cascade로 두면 계정 삭제가 팀 데이터를 날립니다.
  owner_id   uuid not null references auth.users (id) on delete restrict,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index workspaces_owner_id_idx on public.workspaces (owner_id);

create trigger workspaces_set_updated_at
  before update on public.workspaces
  for each row execute function public.set_updated_at();


-- -----------------------------------------------------------------------------
-- 2. 멤버십 (RLS의 축)
-- -----------------------------------------------------------------------------
create table public.workspace_members (
  workspace_id uuid not null references public.workspaces (id) on delete cascade,
  user_id      uuid not null references auth.users (id) on delete cascade,
  role         text not null default 'viewer' check (role in ('owner', 'editor', 'viewer')),
  created_at   timestamptz not null default now(),
  primary key (workspace_id, user_id)
);

-- "내가 속한 워크스페이스 목록" 조회 및 RLS 헬퍼 함수의 조회 경로.
-- PK가 (workspace_id, user_id)라 user_id 단독 조회는 별도 인덱스가 필요합니다.
create index workspace_members_user_id_idx on public.workspace_members (user_id);

-- 워크스페이스 생성 시 소유자를 멤버로 자동 등록.
-- 이게 없으면 멤버가 0명인 워크스페이스가 만들어질 수 있고,
-- 그 워크스페이스는 RLS 하에서 아무에게도 보이지 않아 복구가 불가능해집니다.
create or replace function public.add_owner_as_member()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.workspace_members (workspace_id, user_id, role)
  values (new.id, new.owner_id, 'owner')
  on conflict (workspace_id, user_id) do update set role = 'owner';
  return new;
end;
$$;

create trigger workspaces_add_owner_member
  after insert on public.workspaces
  for each row execute function public.add_owner_as_member();


-- -----------------------------------------------------------------------------
-- 3. Layer 1: 원문 소스 (불변)
-- -----------------------------------------------------------------------------
create table public.raw_sources (
  id           uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces (id) on delete cascade,
  created_by   uuid references auth.users (id) on delete set null,

  title       text not null,
  source_type text not null check (
    source_type in ('article', 'paper', 'book', 'transcript', 'clipping', 'file', 'text', 'url')
  ),

  -- 추출된 평문. source_chunks(0002)가 char_start/char_end로 이 문자열을 가리킵니다.
  content text not null,

  -- 멱등성 키 (P4-QA-01).
  -- 파일이면 원본 바이트의 sha256, 텍스트/URL이면 정규화된 본문의 sha256.
  content_hash text not null,

  -- 원본 파일 보관 (decisions.original_file_retention).
  -- 경로 규칙: {workspace_id}/{raw_source_id}/{filename}
  -- 텍스트 직접 입력처럼 원본 파일이 없는 경우 NULL.
  storage_path text,
  mime_type    text,
  byte_size    bigint check (byte_size is null or byte_size >= 0),

  collection_purpose text,
  metadata           jsonb not null default '{}',
  created_at         timestamptz not null default now(),

  -- 동일 워크스페이스 내 같은 내용 재수집을 차단.
  -- 워크스페이스가 다르면 같은 문서를 각자 보유할 수 있어야 하므로 복합 UNIQUE.
  unique (workspace_id, content_hash)
);

create index raw_sources_workspace_created_idx
  on public.raw_sources (workspace_id, created_at desc);


-- -----------------------------------------------------------------------------
-- 4. Layer 2: 컴파일된 위키
-- -----------------------------------------------------------------------------
create table public.wiki_pages (
  id           uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces (id) on delete cascade,
  created_by   uuid references auth.users (id) on delete set null,

  slug     text not null,
  title    text not null,
  -- 렌즈 필터가 이 컬럼을 그대로 사용합니다 (decisions.lens_filter).
  category text not null check (category in ('concepts', 'entities', 'guides', 'maps')),
  content  text not null,
  aliases  jsonb not null default '[]',

  -- 품질 통제 (P2-QC-01).
  -- explored: 사람만 전이시킵니다. disputed: 시스템이 세팅하고 사람이 해소합니다.
  explored            boolean not null default false,
  confidence          text not null default 'medium'
                        check (confidence in ('high', 'medium', 'low')),
  verification_status text not null default 'unverified'
                        check (verification_status in ('verified', 'partial', 'unverified', 'disputed')),
  disputed            boolean not null default false,

  -- 이 위키를 만든 raw_source id 배열. 이중 Citation의 위키→원문 역추적 경로.
  sources jsonb not null default '[]',

  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),

  unique (workspace_id, slug)
);

-- 렌즈 필터 (/api/graph?lens=concepts)
create index wiki_pages_workspace_category_idx
  on public.wiki_pages (workspace_id, category);

create index wiki_pages_workspace_updated_idx
  on public.wiki_pages (workspace_id, updated_at desc);

-- 검증 대기 목록 조회
create index wiki_pages_unexplored_idx
  on public.wiki_pages (workspace_id)
  where not explored;

create trigger wiki_pages_set_updated_at
  before update on public.wiki_pages
  for each row execute function public.set_updated_at();


-- -----------------------------------------------------------------------------
-- 5. 프롬프트 템플릿
-- -----------------------------------------------------------------------------
create table public.prompt_templates (
  id            uuid primary key default gen_random_uuid(),
  -- NULL = 전역 기본 템플릿 (모든 워크스페이스가 사용)
  workspace_id  uuid references public.workspaces (id) on delete cascade,
  name          text not null,
  target_type   text not null check (target_type in ('compile', 'ask')),
  icon          text,
  system_prompt text not null,
  template      text not null,
  is_default    boolean not null default false,
  created_at    timestamptz not null default now()
);

-- 전역 기본 템플릿은 target_type당 정확히 1개 (P1-SEED-01의 검증 기준을 DB가 강제)
create unique index prompt_templates_global_default_idx
  on public.prompt_templates (target_type)
  where workspace_id is null and is_default;

-- 워크스페이스별 기본 템플릿도 target_type당 1개
create unique index prompt_templates_workspace_default_idx
  on public.prompt_templates (workspace_id, target_type)
  where workspace_id is not null and is_default;

create index prompt_templates_workspace_idx
  on public.prompt_templates (workspace_id, target_type);


-- -----------------------------------------------------------------------------
-- RLS: 정책 없이 활성화 = 전면 거부
--
-- 실제 정책은 0004_rls_policies.sql (P1-SEC-01)에서 부여합니다.
-- 여기서 미리 켜두는 이유: 0001~0003 사이에 테이블이 anon 키에
-- 노출되는 창을 만들지 않기 위해서입니다.
-- service_role 키는 RLS를 우회하므로 마이그레이션/워커는 영향받지 않습니다.
-- -----------------------------------------------------------------------------
alter table public.workspaces        enable row level security;
alter table public.workspace_members enable row level security;
alter table public.raw_sources       enable row level security;
alter table public.wiki_pages        enable row level security;
alter table public.prompt_templates  enable row level security;

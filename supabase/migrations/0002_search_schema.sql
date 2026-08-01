-- =============================================================================
-- NexusWiki 0002: 검색 스키마
--
-- 관련 태스크: P1-DB-02
-- 설계 근거:  checklists.json > decisions.graph_db (Neo4j 제외 → wiki_links)
--             checklists.json > decisions.korean_search (앱 레이어 bigram)
--             HANDOFF.md §1 "5-Way 검색 채널의 정의"
--
-- 5개 검색 채널이 이 마이그레이션에서 물리적으로 완성됩니다.
--   1. wiki_embeddings.embedding   벡터 유사도 (HNSW)
--   2. source_chunks.embedding     벡터 유사도 (HNSW)
--   3. wiki_pages.search_tsv       bigram 어휘 검색 (GIN)   ← 이 파일에서 컬럼 추가
--   4. source_chunks.search_tsv    bigram 어휘 검색 (GIN)
--   5. wiki_links                  N-hop 그래프 확장 (recursive CTE)
--
-- 0001과 동일하게 RLS를 "정책 없이" 켠 상태로 만듭니다 (= 전면 거부).
-- 정책은 0004_rls_policies.sql (P1-SEC-01).
-- =============================================================================


-- -----------------------------------------------------------------------------
-- pgvector
--
-- Supabase 관례에 따라 extensions 스키마에 설치합니다 (pgcrypto, pg_net과 동일).
-- 이 파일에서는 타입/연산자 클래스를 전부 스키마 수식(extensions.vector 등)합니다.
-- 마이그레이션 실행 롤의 search_path에 의존하지 않기 위해서입니다.
-- 애플리케이션 쿼리(`embedding <=> $1`)는 authenticated/anon 롤의 기본
-- search_path에 extensions가 포함되므로 수식 없이 그대로 씁니다.
-- -----------------------------------------------------------------------------
create extension if not exists vector with schema extensions;


-- -----------------------------------------------------------------------------
-- 테넌트 경계를 FK로 강제하기 위한 사전 준비
--
-- 아래 검색 테이블들은 workspace_id를 비정규화해서 들고 있습니다.
-- (RLS 정책과 벡터 검색 필터가 조인 없이 워크스페이스를 좁힐 수 있어야 함)
--
-- 문제는 워커입니다. 워커는 service_role로 붙어 RLS를 우회하므로
-- 잘못된 workspace_id를 넣어도 DB가 막아주지 않습니다 (HANDOFF.md §5).
-- (id, workspace_id) 복합 UNIQUE를 만들어 두면 자식 테이블이 복합 FK를 걸 수 있고,
-- "청크의 workspace_id ≠ 원본 소스의 workspace_id" 조합이 아예 삽입 불가가 됩니다.
-- 코드 실수를 DB가 잡아주는 쪽으로 옮기는 것이 decisions.db_access의 취지입니다.
-- -----------------------------------------------------------------------------
alter table public.raw_sources
  add constraint raw_sources_id_workspace_key unique (id, workspace_id);

alter table public.wiki_pages
  add constraint wiki_pages_id_workspace_key unique (id, workspace_id);


-- -----------------------------------------------------------------------------
-- 1. source_chunks — 이중 Citation의 "원문" 측
--
-- 원안에 존재하지 않던 테이블입니다. 이게 없으면 답변이 위키만 인용할 수 있어
-- 제품의 핵심 약속인 "원문 + 위키 이중 출처"가 구현 불가능합니다.
-- -----------------------------------------------------------------------------
create table public.source_chunks (
  id            uuid primary key default gen_random_uuid(),
  raw_source_id uuid not null,
  workspace_id  uuid not null,

  -- 한 소스 안에서의 순번. 0부터. 인용 표시("3번째 문단")와 재개 가능한
  -- 임베딩 배치(P2-EMB-01)의 커서 역할을 합니다.
  chunk_index int not null check (chunk_index >= 0),

  content text not null,

  -- raw_sources.content에 대한 파이썬 슬라이스 좌표: content[char_start:char_end]
  -- char_end는 배타적(exclusive)입니다. 이 좌표로 원문을 다시 잘랐을 때
  -- 아래 content와 정확히 일치해야 합니다 (P2-ING-02에서 검증).
  char_start int not null check (char_start >= 0),
  char_end   int not null,

  -- 생성 직후엔 NULL. P2-EMB-01이 배치로 채웁니다.
  -- text-embedding-3-small(1536차원).
  embedding extensions.vector(1536),

  -- ⚠️ generated column이 아닙니다. 애플리케이션(P2-BE-02)이 bigram으로
  -- 쪼갠 문자열을 to_tsvector('simple', ...)로 만들어 넣습니다.
  -- DB가 to_tsvector를 직접 돌리면 한국어가 공백 단위로만 분해되어
  -- 검색이 사실상 무용해집니다 (decisions.korean_search).
  search_tsv tsvector,

  -- 이 행을 색인한 토크나이저 버전. 질의 시 토크나이저와 어긋나면
  -- 검색이 "에러 없이 조용히" 안 맞습니다 (HANDOFF.md §5).
  -- 버전별로 남겨 두면 재색인 대상을 전수 재처리 없이 골라낼 수 있습니다.
  --
  -- 질의 측 규칙 (P2-BE-02): bigram 문자열을 to_tsquery에 그대로 넣으면
  -- "한국 국어"처럼 공백으로 이어져 syntax error가 납니다.
  -- phraseto_tsquery('simple', bigram(q))를 쓰세요. bigram들이 <-> 로 묶여
  -- 인접성까지 검사하므로 부분 문자열 매칭 의미가 정확히 보존됩니다.
  -- (plainto_tsquery는 & 로 묶여 순서가 뒤바뀐 오탐이 섞입니다.)
  tsv_tokenizer_version smallint,

  created_at timestamptz not null default now(),

  -- 빈 청크 금지 + 좌표 역전 금지
  constraint source_chunks_char_range_check check (char_end > char_start),
  -- 같은 소스의 같은 순번은 하나뿐. 재수집/재처리 시 upsert 키.
  constraint source_chunks_source_index_key unique (raw_source_id, chunk_index),
  -- 청크는 원본 소스와 반드시 같은 워크스페이스에 있어야 합니다.
  constraint source_chunks_raw_source_fkey
    foreign key (raw_source_id, workspace_id)
    references public.raw_sources (id, workspace_id) on delete cascade
);

create index source_chunks_workspace_idx
  on public.source_chunks (workspace_id);

-- 채널 2: 벡터 유사도.
-- ⚠️ workspace_id로 필터링한 벡터 검색은 HNSW의 사후 필터링 때문에
-- 결과가 k개보다 적게 나올 수 있습니다. 검색 쿼리(P2-BE-01)에서
-- `set local hnsw.iterative_scan = strict_order`를 켜세요 (pgvector 0.8+).
create index source_chunks_embedding_idx
  on public.source_chunks using hnsw (embedding extensions.vector_cosine_ops);

-- 채널 4: bigram 어휘 검색
create index source_chunks_search_tsv_idx
  on public.source_chunks using gin (search_tsv);


-- -----------------------------------------------------------------------------
-- 2. wiki_embeddings — 컴파일된 위키의 벡터 표현
--
-- 위키 본문이 길면 여러 청크로 쪼개므로 wiki_pages와 1:N입니다.
-- (원안 명세엔 chunk_index가 없었지만, 순번이 없으면 재임베딩 시 멱등한
--  upsert 키가 없어 중복 행이 쌓입니다.)
-- -----------------------------------------------------------------------------
create table public.wiki_embeddings (
  id           uuid primary key default gen_random_uuid(),
  wiki_id      uuid not null,
  workspace_id uuid not null,

  chunk_index   int  not null check (chunk_index >= 0),
  chunk_content text not null,

  embedding extensions.vector(1536),

  created_at timestamptz not null default now(),

  constraint wiki_embeddings_wiki_index_key unique (wiki_id, chunk_index),
  constraint wiki_embeddings_wiki_fkey
    foreign key (wiki_id, workspace_id)
    references public.wiki_pages (id, workspace_id) on delete cascade
);

create index wiki_embeddings_workspace_idx
  on public.wiki_embeddings (workspace_id);

-- 채널 1: 벡터 유사도 (위 iterative_scan 주의사항 동일)
create index wiki_embeddings_embedding_idx
  on public.wiki_embeddings using hnsw (embedding extensions.vector_cosine_ops);


-- -----------------------------------------------------------------------------
-- 3. wiki_links — Neo4j를 대체하는 그래프 간선
--
-- to_wiki_id IS NULL = 미해결 링크(red link). 아직 존재하지 않는 위키를
-- 가리키는 상태이며, 그 자체로 "다음에 만들 위키" 목록이 됩니다.
-- 나중에 target_slug와 같은 slug의 위키가 생기면 to_wiki_id를 채워 해소합니다.
-- -----------------------------------------------------------------------------
create table public.wiki_links (
  id           uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces (id) on delete cascade,

  from_wiki_id uuid not null,
  -- 링크 원문에 적힌 대상 slug. to_wiki_id가 채워져도 보존합니다
  -- (대상 위키가 삭제되면 이 slug로 다시 red link가 되어야 하므로).
  target_slug  text not null check (char_length(btrim(target_slug)) > 0),
  to_wiki_id   uuid,

  -- to_wiki_id와 따로 관리하면 둘이 어긋날 수 있으므로 파생 컬럼으로 고정합니다.
  -- (한국어 토크나이징과 무관하므로 generated column이 안전한 자리입니다.)
  resolved boolean not null generated always as (to_wiki_id is not null) stored,

  created_at timestamptz not null default now(),

  -- 같은 문서에서 같은 대상으로 가는 간선은 하나. 재컴파일 시 upsert 키.
  constraint wiki_links_from_target_key unique (from_wiki_id, target_slug),
  constraint wiki_links_no_self_link check (to_wiki_id is null or to_wiki_id <> from_wiki_id),

  -- 출발 위키가 사라지면 간선도 사라집니다.
  constraint wiki_links_from_fkey
    foreign key (from_wiki_id, workspace_id)
    references public.wiki_pages (id, workspace_id) on delete cascade,

  -- 도착 위키가 사라지면 red link로 되돌립니다.
  -- 복합 FK지만 MATCH SIMPLE이므로 to_wiki_id가 NULL이면 검사를 건너뜁니다
  -- = red link 삽입 가능. workspace_id까지 NULL이 되지 않도록
  -- PG15+ 의 컬럼 지정 SET NULL을 씁니다.
  constraint wiki_links_to_fkey
    foreign key (to_wiki_id, workspace_id)
    references public.wiki_pages (id, workspace_id) on delete set null (to_wiki_id)
);

-- 채널 5 정방향: "이 문서가 가리키는 것들" (recursive CTE의 하강 방향)
create index wiki_links_from_idx
  on public.wiki_links (workspace_id, from_wiki_id);

-- 채널 5 역방향: 백링크 "이 문서를 가리키는 것들"
create index wiki_links_to_idx
  on public.wiki_links (workspace_id, to_wiki_id)
  where to_wiki_id is not null;

-- 새 위키 생성 시 "이 slug를 기다리던 red link" 일괄 해소 (P2-QC-01)
create index wiki_links_unresolved_slug_idx
  on public.wiki_links (workspace_id, target_slug)
  where to_wiki_id is null;


-- -----------------------------------------------------------------------------
-- 4. wiki_pages 어휘 검색 컬럼 (채널 3)
--
-- 0001에는 없던 컬럼입니다. source_chunks.search_tsv와 완전히 동일한 규칙:
-- generated column 금지, 애플리케이션이 bigram 토크나이즈해서 채웁니다.
-- -----------------------------------------------------------------------------
alter table public.wiki_pages
  add column search_tsv            tsvector,
  add column tsv_tokenizer_version smallint;

create index wiki_pages_search_tsv_idx
  on public.wiki_pages using gin (search_tsv);


-- -----------------------------------------------------------------------------
-- RLS: 정책 없이 활성화 = 전면 거부 (0001과 동일한 이유)
-- 실제 정책은 0004_rls_policies.sql (P1-SEC-01).
-- wiki_pages는 0001에서 이미 켜져 있습니다.
-- -----------------------------------------------------------------------------
alter table public.source_chunks   enable row level security;
alter table public.wiki_embeddings enable row level security;
alter table public.wiki_links      enable row level security;

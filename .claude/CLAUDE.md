<!-- GSD:project-start source:PROJECT.md -->

## Project

**NexusWiki**

원시 소스(PDF · URL · 텍스트)를 넣으면 LLM이 상호 링크된 위키로 컴파일하고, 5채널 하이브리드 검색으로 **원문과 위키 양쪽을 함께 인용한 답변**을 돌려주는 Cairni 스타일 Living Wiki SaaS입니다. 팀 단위 워크스페이스가 기본 단위이며, 테넌트 격리는 애플리케이션이 아니라 Postgres RLS가 강제합니다. 사용 대상은 흩어진 문서를 하나의 검증 가능한 지식 베이스로 만들고 싶은 소규모 팀입니다.

**Core Value:** 질문에 대한 답이 **원문 청크와 컴파일된 위키 페이지 양쪽으로 추적 가능해야 한다** — 이중 Citation이 무너지면 이 제품은 그냥 또 하나의 RAG 챗봇입니다.

### Constraints

- **Tech stack**: Supabase(Postgres 17 + Auth + Storage) · FastAPI · Next.js 15 App Router · pgvector — 데이터 계층이 이미 이 전제로 구현·검증 완료됨
- **Tech stack**: LLM은 OpenRouter 경유, 모델은 env `LLM_MODEL`(기본 `claude-sonnet-4-6`) — 모델 교체 자유도 확보. 대신 Anthropic 네이티브 프롬프트 캐싱과 네이티브 `output_config.format`을 포기. (OpenRouter 자체의 `response_format: {type:"json_schema"}`는 엔드포인트별로 지원되므로 `require_parameters: true`와 능력 탐지를 전제로 선택적 최적화로 쓸 수 있음 — 프롬프트+Pydantic+3회 재시도는 그와 무관하게 필수 백스톱)
- **Deployment**: Supabase 리전 `ap-southeast-1`(싱가포르) + Railway `asia-southeast1` — Railway에 서울·도쿄 리전이 없어 교차 리전 왕복이 5채널마다 곱해짐. **리전은 프로젝트 생성 후 변경 불가**
- **Security**: Next.js는 15.2.3 이상 필수 — CVE-2025-29927은 `x-middleware-subrequest` 헤더 위조로 미들웨어를 건너뛰는데, 이 앱의 테넌트 게이트가 미들웨어임
- **Security**: 사용자 요청 경로는 요청자 JWT(`user_client`), `service_role`은 워커와 마이그레이션 전용 — `service_role`은 BYPASSRLS라 사용자 경로에 쓰는 순간 38개 격리 정책이 전부 장식이 됨
- **Compatibility**: 마이그레이션 `0005`(Storage)는 클라우드 첫 `db push` **이전에** 반드시 적용 — 이후에 넣으면 로컬/클라우드 순서가 어긋남
- **Dependencies**: 로컬 포트는 544xx 고정 — 같은 머신의 `zettlink` 스택이 543xx를 점유. 튜토리얼의 `54321`/`54322`를 쓰면 다른 프로젝트 DB에 붙음
- **Dependencies**: 로컬 `psql` 없음 — `docker exec -it supabase_db_NexusWiki psql -U postgres -d postgres` 사용
- **Performance**: 벡터 검색은 post-filter — `set local hnsw.iterative_scan = strict_order`(pgvector 0.8+) 필수, k보다 적게 돌아올 수 있음
- **Correctness**: 색인 시점과 질의 시점 토크나이저가 동일해야 함 — 불일치는 조용히 실패함. `tsv_tokenizer_version`이 재색인 범위를 좁히기 위해 존재
- **Budget**: Railway Hobby $5/mo + Supabase + LLM 종량 — 개인 프로젝트 수준 예산

<!-- GSD:project-end -->

<!-- GSD:stack-start source:codebase/STACK.md -->

## Technology Stack

## Languages

- **SQL (PostgreSQL 17 dialect)** — the entire implemented codebase. `supabase/migrations/0001_core_schema.sql`, `0002_search_schema.sql`, `0003_jobs.sql`, `0004_rls_policies.sql`, `0006_seed_prompts.sql` (1,288 lines total)
- **TOML** — local stack configuration. `supabase/config.toml`
- **JSON** — task/decision ledger. `checklists.json`
- **Markdown** — session handoff. `HANDOFF.md`
- **Python** (FastAPI API + queue worker) — `apps/api/` · `apps/worker/` (task `P0-INIT-02`)
- **TypeScript** (Next.js 15 dashboard, `strict` mode) — `apps/dashboard/` (task `P0-INIT-03`)

## Runtime

- **PostgreSQL 17** — `major_version = 17` in `supabase/config.toml:32`
- **Supabase local stack via Docker** — containers named `supabase_*_NexusWiki`
- **Supabase CLI 2.33.2** (upstream latest 2.111.0; upgrade deliberately deferred until Phase 1 closes — `config.toml` schema may change)
- Python 3.12 runtime for `api` + `worker` services
- Node.js runtime for the Next.js dashboard
- 루트 `pyproject.toml`과 `uv.lock`으로 Python 워크스페이스를 관리한다. dashboard는 자체 `pnpm-lock.yaml`을 쓴다.
- Python 패키지 매니저는 `uv`, dashboard 패키지 매니저는 `pnpm`이다.

## Frameworks

- **Supabase platform** — Postgres + PostgREST + GoTrue Auth + Storage + Realtime, all configured in `supabase/config.toml`
- **PostgREST** — auto-exposed API over `public` and `graphql_public` schemas (`config.toml:11`), `max_rows = 1000`
- **FastAPI** — HTTP API layer (`P0-INIT-02`)
- **Pydantic / pydantic-settings** — settings + LLM structured-output validation with 3-attempt retry (`decisions.llm.structured_output`)
- **Next.js 15 (App Router)** + **Tailwind CSS** — dashboard (`P0-INIT-03`)
- **Cytoscape** — knowledge graph canvas (`P3-UI-03`)
- **Implemented:** none as automated suites. Migration verification was performed ad hoc via `psql` + `EXPLAIN ANALYZE` inside the DB container; results are recorded in `HANDOFF.md` §3–3d and `checklists.json` task `verification` fields.
- **pytest** for the Python API/core; **Vitest + Testing Library** for the dashboard (`P0-INIT-03`)
- **Supabase CLI** — `supabase start`, `supabase db reset`, `supabase stop`
- **Docker Desktop** — required host dependency for the local stack
- `pre-commit` running `ruff` (Python) + `prettier` (TS) — `P0-INIT-01`
- `.editorconfig`, root `README.md` — `P0-INIT-01`

## Key Dependencies

- **pgvector** (`vector` extension, local v0.8.0) — installed into the `extensions` schema at `supabase/migrations/0002_search_schema.sql:30`. All references are schema-qualified (`extensions.vector(1536)`, `extensions.vector_cosine_ops`) so behavior does not depend on the executing role's `search_path`.
- **pgcrypto / `gen_random_uuid()`** — UUID primary keys across all 9 tables
- **HNSW indexes** — `source_chunks_embedding_idx`, `wiki_embeddings_embedding_idx` (cosine)
- **GIN tsvector indexes** — `wiki_pages_search_tsv_idx`, `source_chunks_search_tsv_idx` over app-generated bigram `tsvector('simple', …)`
- `httpx`-style HTTP client for OpenRouter + OpenAI embeddings
- `pypdf` for PDF text extraction (`P2-ING-02`)
- Postgres job queue in-database: `jobs` table + `claim_job` / `complete_job` / `fail_job` / `reap_stale_jobs`, `FOR UPDATE SKIP LOCKED` (`supabase/migrations/0003_jobs.sql`). `EXECUTE` revoked from `anon` and `authenticated`; `service_role` only.

## Configuration

- `supabase/config.toml` is the only committed config. It reads secrets by reference, never by value: `OPENAI_API_KEY` (Studio AI, line 86), `SUPABASE_AUTH_SMS_TWILIO_AUTH_TOKEN`, `SUPABASE_AUTH_EXTERNAL_APPLE_SECRET`, `S3_HOST` / `S3_REGION` / `S3_ACCESS_KEY` / `S3_SECRET_KEY`.
- No `.env` or `.env.example` exists on disk. `.gitignore` excludes `.env`, `.env.*` (allowing `.env.example`) and `supabase/.env`.

| Service | URL / Port |
|---|---|
| API | `http://127.0.0.1:54421` |
| DB | `postgresql://…@127.0.0.1:54422/postgres` |
| Studio | `http://127.0.0.1:54423` |
| Inbucket | `http://127.0.0.1:54424` |
| Analytics | `54427` |
| Pooler (disabled) | `54429` |
| Shadow DB | `54420` |

- Implemented: `supabase/config.toml` only
- `pyproject.toml`, `uv.lock`, `apps/api/pyproject.toml`, `apps/worker/pyproject.toml`, `apps/dashboard/package.json`, `apps/dashboard/vitest.config.ts`, `.pre-commit-config.yaml`, `.editorconfig`, `README.md`, `Dockerfile`, `railway.json`

## Platform Requirements

- Docker Desktop (Docker engine has crashed once here — symptom is HTTP 500 with `apiproxy: connection refused`; fix is restarting Docker Desktop)
- Supabase CLI 2.33.2
- No local `psql` — use `docker exec -it supabase_db_NexusWiki psql -U postgres -d postgres`
- Disk pressure noted: 94% used, `Docker.raw` at 61GB
- **Supabase Cloud** — project **created and ACTIVE_HEALTHY** in region `ap-southeast-1` (Singapore); migrations `0001`~`0007` applied. Region is fixed at creation and cannot be changed. Evidence: `docs/ops/cloud-bootstrap-record.md` (`0001`~`0006`), `docs/ops/migration-0007-record.md` (`0007`)
- **Railway** — one project, two services (`api` web + `worker` resident). Hobby $5/mo is billed per workspace, not per service; CPU-actual billing suits LLM-wait workers.
- **[PLANNED] Vercel** — frontend hosting
- Alternatives evaluated and rejected: Fly.io (~$6.5/mo), Render ($14/mo fixed)

## Known Stack Risks

- `0005` is a **gap in the migration sequence**, reserved for `P1-STO-01` (Storage buckets). Local `db reset` applies by filename order so it is harmless today, but adding `0005` *after* pushing `0006` to a cloud project breaks ordering. Must land before `P0-INIT-04`.
- OpenRouter routing forfeits Anthropic native prompt caching and `output_config.format`; compiler cost scales linearly with source count (revisit in `P4-OPS-01`).

<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->

## Conventions

## Naming Patterns

- Migrations: `NNNN_snake_case_topic.sql`, zero-padded 4-digit sequence — `supabase/migrations/0001_core_schema.sql`, `0002_search_schema.sql`, `0003_jobs.sql`, `0004_rls_policies.sql`, `0006_seed_prompts.sql`.
- **Number order is apply order.** `0005` is deliberately reserved for the Storage bucket migration (`supabase/migrations/0005_storage.sql`, task `P1-STO-01`) and must land *before* a cloud project is created — see `HANDOFF.md` §3e.
- Python: `snake_case.py` under `apps/api/src/api/` 또는 `apps/worker/src/worker/`; 공유 코드는 `packages/core/src/nexuswiki_core/`에 둔다.
- Python tests: `apps/api/tests/test_<module>.py` 또는 각 workspace member의 `tests/`.
- React components (planned): `PascalCase.tsx` under `apps/dashboard/components/` — `WorkspaceSwitcher.tsx`, `AskCanvas.tsx`, `GraphCanvas.tsx`.
- Next.js routes (planned): App Router lowercase segments with route groups — `apps/dashboard/app/(auth)/login/page.tsx`.
- All lowercase `snake_case`; SQL keywords are also lowercase (`create table`, `on delete cascade`). No uppercase keywords anywhere in `supabase/migrations/`.
- Tables: plural nouns — `workspaces`, `workspace_members`, `raw_sources`, `wiki_pages`, `source_chunks`, `wiki_embeddings`, `wiki_links`, `prompt_templates`, `jobs`.
- Indexes: `<table>_<columns>_idx` — `workspaces_owner_id_idx`, `wiki_pages_workspace_category_idx`, `jobs_poll_idx`, `source_chunks_embedding_idx`.
- Triggers: `<table>_<action>` — `workspaces_set_updated_at`, `wiki_pages_set_updated_at`, `jobs_set_updated_at`, `workspaces_add_owner_member`.
- Named CHECK constraints: `<table>_<intent>` — `jobs_lock_consistency` (`supabase/migrations/0003_jobs.sql:65`).
- Functions: verb-first `snake_case`, always schema-qualified as `public.<name>` at definition and call sites — `public.set_updated_at()`, `public.is_workspace_member()`, `public.claim_job()`.
- Function parameters: `p_` prefix to avoid collision with column names — `p_worker_id`, `p_job_id`, `p_backoff`, `p_max_backoff`, `p_timeout` (`supabase/migrations/0003_jobs.sql:103-196`). RLS helper params use a short domain name instead (`ws_id`, `min_role`).
- Enumerations are `text` columns with an inline `check (col in (...))`, **not** Postgres `enum` types — `wiki_pages.category`, `jobs.status`, `workspace_members.role`.
- One documented exception: `jobs.type` has no enumeration CHECK (only non-empty), because job kinds churn during Phase 2. The worker must route unknown `type` values straight to `dead` with `last_error` set — rationale is inline at `supabase/migrations/0003_jobs.sql:31-36`.

## Code Style

- SQL: 2-space indent, one column per line, aligned inline comments, `-- ---` rule lines separating numbered sections within a file.
- Python (planned): `ruff` via pre-commit (`P0-INIT-01`, target file `.pre-commit-config.yaml`).
- TypeScript/TSX (planned): `prettier` via pre-commit; TypeScript `strict` mode with `tsc --noEmit` clean (`P0-INIT-03`).
- `.pre-commit-config.yaml`이 Python에는 ruff, dashboard에는 prettier를 적용한다.
- Gate: `pre-commit run --all-files` must pass from the repo root (`P0-INIT-01` verification).
- All comments, commit messages, and docs are **Korean**. Identifiers, keywords, and file names stay English/ASCII. Match this — a Korean codebase with English identifiers is the house style, not an accident.

## File Header Convention

- **Cite the task ID** (`P1-DB-03`) and the **decision key** in `checklists.json` (`decisions.job_queue`). Never restate a decision's reasoning inline — point at the ledger.
- 결정의 수명이 인용 계층을 정한다. 프로젝트 수명 전체의 스택·배포·DB 접근 결정은 `checklists.json > decisions.<key>`를, 한 페이즈 안에서만 유효한 결정은 `.planning/phases/NN-*/NN-CONTEXT.md`의 `NN-CONTEXT.md > D-XX`를 인용한다. 같은 근거를 두 계층에 되풀이하지 않는다.
- Name downstream consumers by task ID so a reader knows who depends on the object.
- ASCII state/flow diagrams live in the header when the file encodes a state machine (`supabase/migrations/0003_jobs.sql:9-15`).

## Comment Conventions

- Every non-obvious DDL choice carries a "what breaks otherwise" note. Example, `supabase/migrations/0001_core_schema.sql:36-38`:
- `⚠️` prefixes a footgun that will silently corrupt data or security if ignored — `supabase/migrations/0003_jobs.sql:186`, `supabase/migrations/0004_rls_policies.sql:17`, `:30`.
- Deviations from the original plan are annotated in-file **and** recorded in `checklists.json` → `<task>.deviations_from_plan`. Both must be updated together.
- Public functions get a `comment on function ... is '...'` describing contract and caller restriction — see `supabase/migrations/0003_jobs.sql:130`.
- Placeholder/path conventions are documented at the column that stores them (e.g. storage path rule `{workspace_id}/{raw_source_id}/{filename}` at `supabase/migrations/0001_core_schema.sql:108`).

## SQL Patterns (mandatory)

## Error Handling

- An RLS `USING` failure on UPDATE/DELETE returns **0 rows, not an exception**. The API must map **affected rows == 0 → HTTP 403**.
- A `WITH CHECK` violation surfaces as SQLSTATE `42501` → also 403.
- Config errors fail fast at boot: a missing environment variable must abort startup naming the specific key (`P0-INIT-02` verification).
- LLM structured output uses prompt + Pydantic validation + **3 retries** (`decisions.structured_output`); OpenRouter cannot use Anthropic native output formats.

## Logging

- 구조화 로깅은 `packages/core/src/nexuswiki_core/logging.py`가 소유하며 `apps/api`와 `apps/worker`가 함께 사용한다.
- SQL-side diagnostics are appended to `jobs.last_error` with a `[reaped]` marker rather than logged out-of-band (`supabase/migrations/0003_jobs.sql:199-201`).

## Module Design

## Design Tokens

- CSS variable naming: `--<category>-<name>[-<modifier>]` — `--color-primary`, `--color-primary-active`, `--color-surface-soft`.
- Categories: `color`, `typography` (fontFamily + named scales `display-xl`/`display-lg`/`title-md`/`body-md`/`body-sm`), `border.radius` (`none`…`full`), `spacing` (`xxs`…`section`).
- The CSS file is sectioned with numbered banner comments (`1. COLOR TOKENS`) and each token carries a usage comment.
- Consume tokens; do not introduce raw hex values or ad-hoc px spacing in components.

## Commit Conventions

- Form: `type(scope): <migration number or subject> — <what changed, concretely>`.
- Scope so far is `db`; expect `api`, `worker`, `web` as apps land.
- Migration commits lead with the migration number.
- Subjects quantify (`9개 테이블 전체`, `ask 4종 + compile 1종`) rather than saying "add policies".
- One task = one commit. Commits map 1:1 onto `checklists.json` task IDs.

## Task Ledger Convention

- Set `status` (`pending` → `in_progress` → `done`).
- Record `verification_result` with `date`, `method`, and a `results` array of pass statements.
- Record any DDL/design divergence under `deviations_from_plan` with its reason.
- Never restate rationale in a second place — link to `decisions.<key>`.
- No derived/summary fields (they go stale immediately) and no `$schema` — per `_notes` in `checklists.json`.

<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->

## Architecture

## System Overview

```text

```

## Component Responsibilities

| Component | Responsibility | File | Status |
|-----------|----------------|------|--------|
| Core schema | Workspaces, membership, raw sources, wiki pages, prompt templates; RLS enabled with no policies (deny-all) | `supabase/migrations/0001_core_schema.sql` | IMPLEMENTED |
| Search schema | `source_chunks`, `wiki_embeddings`, `wiki_links`, `wiki_pages.search_tsv`; HNSW + GIN indexes | `supabase/migrations/0002_search_schema.sql` | IMPLEMENTED |
| Job queue | `jobs` table + `claim_job`/`complete_job`/`fail_job`/`reap_stale_jobs` (SKIP LOCKED) | `supabase/migrations/0003_jobs.sql` | IMPLEMENTED |
| Tenant isolation | RLS policies on all 9 tables + `SECURITY DEFINER` membership helpers + owner-protection trigger | `supabase/migrations/0004_rls_policies.sql` | IMPLEMENTED |
| Storage bucket | Private `sources` bucket, membership-based storage policies | `supabase/migrations/0005_storage.sql` | PLANNED (P1-STO-01) |
| Prompt seeds | 5 global templates (`workspace_id IS NULL`): 1 compile + 4 ask | `supabase/migrations/0006_seed_prompts.sql` | IMPLEMENTED |
| Local stack config | Non-default ports 544xx, Postgres major 17, storage/auth toggles | `supabase/config.toml` | IMPLEMENTED |
| API service | JWT auth, workspace context, read APIs, ask, ingest | `apps/api/` | PLANNED |
| Worker service | Poll queue, parse/chunk, LLM compile, embed, link sync | `apps/worker/` | PLANNED |
| Dashboard | Auth, dropzone, ask UI, Cytoscape canvas, wiki viewer | `apps/dashboard/` | PLANNED |
| Task ledger | 32 tasks, 10 locked decisions, 4 open questions | `checklists.json` | IMPLEMENTED |
| Session handoff | Current state, deviations, traps | `HANDOFF.md` | IMPLEMENTED |
| Architecture explainer | Rendered HTML walkthrough of DB + 5-way search | `docs/architecture/` | IMPLEMENTED |

## Pattern Overview

- **Isolation lives in the database, not the app.** RLS is enabled in the same migration that creates each table, before any policy exists (deny-all window is never open). See `supabase/migrations/0001_core_schema.sql:214-219`.
- **Hybrid DB access.** User request paths use the requester's JWT so RLS enforces isolation; only worker and migrations use `service_role` (BYPASSRLS). `checklists.json > decisions.db_access`.
- **Composite FKs carry the tenant.** `raw_sources` and `wiki_pages` have `(id, workspace_id)` UNIQUE so child tables use composite FKs — a worker that bypasses RLS still cannot cross tenants (`supabase/migrations/0002_search_schema.sql:45-49`).
- **Korean lexical search is an application concern.** `search_tsv` is deliberately NOT a generated column; the app writes bigram-tokenized `to_tsvector('simple', ...)` values, and `tsv_tokenizer_version` records which tokenizer produced each row.
- **Queue state transitions only through functions.** `jobs` must never be UPDATEd directly; attempt accounting and lock-consistency CHECKs live inside the four SECURITY INVOKER functions, all revoked from `anon`/`authenticated`.

## Layers

- Purpose: preserve original material verbatim; the "raw source" half of dual citation
- Location: `public.raw_sources`, `public.source_chunks` (`supabase/migrations/0001_core_schema.sql:90`, `0002_search_schema.sql:58`)
- Contains: extracted plain text, `content_hash` idempotency key, `storage_path` to the original file, chunk slices with `char_start`/`char_end`
- Depends on: `workspaces`
- Used by: search channels 2 and 4, dual citation payloads
- Constraint: **no UPDATE policy exists** — immutability is enforced by the absence of a policy, not by convention
- Purpose: LLM-compiled, human-verifiable knowledge pages
- Location: `public.wiki_pages`, `public.wiki_embeddings`, `public.wiki_links`
- Contains: slug/title/category/content, quality flags (`explored`, `confidence`, `verification_status`, `disputed`), source backreferences
- Depends on: Layer 1
- Used by: search channels 1, 3, 5; the wiki viewer and canvas
- Purpose: decouple ingest requests from long-running LLM work
- Location: `public.jobs` + four functions (`supabase/migrations/0003_jobs.sql`)
- Depends on: `workspaces`
- Used by: ingest API (producer, PLANNED) and worker (consumer, PLANNED)
- Purpose: tenant isolation and role grading
- Location: `supabase/migrations/0004_rls_policies.sql`
- Contains: `is_workspace_member(uuid)`, `workspace_role(uuid)`, `has_workspace_role(uuid, text)`, `protect_owner_membership()` trigger, 20+ policies

## Data Flow

### Read path — question to dual-cited answer [PLANNED, schema IMPLEMENTED]

### Write path — source to wiki [PLANNED, schema IMPLEMENTED]

### Job state machine [IMPLEMENTED]

```text

```

- All durable state is Postgres. There is no cache, queue broker, or graph store.
- Job progress is surfaced directly to the frontend by reading `jobs` (members have SELECT only).

## Key Abstractions

- Purpose: the tenancy root; every domain table carries `workspace_id`
- Files: `supabase/migrations/0001_core_schema.sql:32-84`
- Pattern: `workspaces.owner_id` + `workspace_members(workspace_id, user_id, role)`; an AFTER INSERT trigger auto-registers the owner as a member so a zero-member (permanently invisible) workspace cannot exist
- Purpose: break RLS infinite recursion (`42P17`) on `workspace_members`
- Files: `supabase/migrations/0004_rls_policies.sql:44-95`
- Pattern: `security definer stable set search_path = public`; each returns only the caller's own membership (`auth.uid()` is fixed inside), so granting to `authenticated` is safe
- Purpose: the only sanctioned way to mutate `jobs`
- Files: `supabase/migrations/0003_jobs.sql:103-212`
- Pattern: `claim_job(worker_id, types[])`, `complete_job(job_id)`, `fail_job(job_id, error, backoff, max_backoff)`, `reap_stale_jobs(timeout)` — all `service_role`-only
- Purpose: an outbound wiki link to a page that does not exist yet; doubles as the "next page to write" backlog
- Files: `supabase/migrations/0002_search_schema.sql:163-209`
- Pattern: `to_wiki_id IS NULL`, `resolved` is a stored generated column, target deletion uses `on delete set null (to_wiki_id)` so links revert to red instead of nulling `workspace_id`
- Purpose: swappable compile/ask prompts, global (`workspace_id IS NULL`) or per-workspace
- Files: `supabase/migrations/0001_core_schema.sql:180-204`, `0006_seed_prompts.sql`
- Pattern: `{{variable}}` double-brace placeholders; exactly one default per `target_type` enforced by partial unique indexes

## Entry Points

- Location: `supabase/migrations/`
- Triggers: `supabase db reset` / `supabase db push`
- Order: `0001` → `0002` → `0003` → `0004` → (`0005` reserved) → `0006`
- Location: `supabase/config.toml`
- Ports: API 54421, DB 54422, Studio 54423, Inbucket 54424, Analytics 54427, Pooler 54429, shadow DB 54420 — **not** the Supabase defaults, because another project (`zettlink`) holds 5432x on this machine

## Architectural Constraints

- **Three roles, three privilege levels.** `anon` has no policies at all (fully denied). `authenticated` is governed entirely by RLS. `service_role` is BYPASSRLS — worker code **must** state `workspace_id` filters explicitly.
- **RLS violations are not always errors.** A `USING`-blocked UPDATE/DELETE returns **0 rows, no exception**. The API must map *affected rows = 0* to 403. `WITH CHECK` violations do raise `42501`.
- **Vector search post-filters.** `where workspace_id = $1 order by embedding <=> $2 limit k` lets HNSW pick k first, then filters — fewer than k rows can come back. RLS itself behaves as the same post-filter. Search queries must set `set local hnsw.iterative_scan = strict_order` (pgvector 0.8+).
- **Jobs are at-least-once.** `reap_stale_jobs` default timeout is 15 minutes; a timeout shorter than the longest healthy LLM job causes double processing. All handlers must be idempotent — the three upsert keys `(workspace_id, slug)`, `(raw_source_id, chunk_index)`, `(wiki_id, chunk_index)` exist for exactly this reason.
- **Tokenizer version coupling.** Index-time and query-time tokenizers must be identical; a mismatch fails silently. `tsv_tokenizer_version` on `source_chunks` and `wiki_pages` exists to scope re-indexing.
- **Migration numbering gap.** `0005` is reserved for Storage and must land **before** the first cloud `db push`, otherwise cloud ordering diverges from local.
- **Global state:** none in code (no application code exists yet). Postgres is the single shared mutable store.
- **Circular imports:** not applicable.

## Anti-Patterns

### Using `service_client()` on a user request path

### UPDATEing `jobs` directly

### Feeding a bigram string to `to_tsquery`

### Making `search_tsv` a generated column

### Using `str.format` on prompt templates

### Assembling LLM context without citation anchors

## Error Handling

- CHECK constraints for every enum (`source_type`, `category`, `confidence`, `verification_status`, `role`, `kind`) — job `type` is the one deliberate exception, so the worker must dead-letter unknown types with `last_error`
- Partial unique indexes enforce "exactly one default template per `target_type`"
- Triggers guard structural invariants: `add_owner_as_member`, `protect_owner_membership`
- Retry/dead-letter is a queue concern, with exponential backoff `base * 2^(attempts-1)` capped by `p_max_backoff`
- API mapping (PLANNED): rows affected 0 → 403; `42501` → 403; missing membership → 403; no token → 401

## Cross-Cutting Concerns

<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->

## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, `.github/skills/`, or `.codex/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->

## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:

- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->

## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->

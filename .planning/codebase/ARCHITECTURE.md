<!-- refreshed: 2026-08-01 -->
# Architecture

**Analysis Date:** 2026-08-01

> **Implementation status.** Only the database layer exists as code today: five SQL migrations under `supabase/migrations/` plus `supabase/config.toml`. Everything else (FastAPI backend, worker process, Next.js dashboard) is **PLANNED** and specified in `checklists.json` and `HANDOFF.md`. Sections below are tagged **[IMPLEMENTED]** or **[PLANNED]**. Do not treat planned paths as existing files.

## System Overview

```text
┌─────────────────────────────────────────────────────────────┐
│                    Frontend  [PLANNED]                       │
│                 Next.js 15 App Router                        │
├──────────────────┬──────────────────┬───────────────────────┤
│  Ask / Citation  │  Knowledge Canvas│   Source Dropzone      │
│ `apps/dashboard` │ `apps/dashboard` │  `apps/dashboard`      │
└────────┬─────────┴────────┬─────────┴──────────┬────────────┘
         │ user JWT         │                    │
         ▼                  ▼                    ▼
┌─────────────────────────────────────────────────────────────┐
│              FastAPI API service  [PLANNED]                  │
│  `apps/fastapi-backend/main.py` · routers/ · services/       │
│  auth (Supabase JWT) → user_client(access_token) → RLS       │
└───────┬──────────────────────────────────────┬──────────────┘
        │ enqueue job                          │ read/query
        ▼                                      │
┌───────────────────────────────┐              │
│   Worker service  [PLANNED]   │              │
│ `apps/fastapi-backend/worker.py`             │
│ claim_job → parse/compile/    │              │
│ embed → complete_job          │              │
│ service_client() = BYPASSRLS  │              │
└───────┬───────────────────────┘              │
        │                                      │
        ▼                                      ▼
┌─────────────────────────────────────────────────────────────┐
│         Supabase Postgres 17  [IMPLEMENTED]                  │
│  `supabase/migrations/0001..0006`                            │
│  9 tables · RLS on all · queue functions · pgvector HNSW     │
│  + Supabase Storage bucket `sources`  [PLANNED: 0005]        │
└─────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│  External: OpenRouter (LLM) · OpenAI (embeddings)  [PLANNED] │
└─────────────────────────────────────────────────────────────┘
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
| API service | JWT auth, workspace context, read APIs, ask, ingest | `apps/fastapi-backend/` | PLANNED |
| Worker service | Poll queue, parse/chunk, LLM compile, embed, link sync | `apps/fastapi-backend/worker.py` | PLANNED |
| Dashboard | Auth, dropzone, ask UI, Cytoscape canvas, wiki viewer | `apps/dashboard/` | PLANNED |
| Task ledger | 32 tasks, 10 locked decisions, 4 open questions | `checklists.json` | IMPLEMENTED |
| Session handoff | Current state, deviations, traps | `HANDOFF.md` | IMPLEMENTED |
| Architecture explainer | Rendered HTML walkthrough of DB + 5-way search | `docs/architecture/` | IMPLEMENTED |

## Pattern Overview

**Overall:** Database-enforced multi-tenant SaaS — a two-layer knowledge store (immutable Layer 1 sources → compiled Layer 2 wiki) with a Postgres-native job queue and hybrid retrieval. No graph database; graph traversal is a recursive CTE over `wiki_links`.

**Key Characteristics:**
- **Isolation lives in the database, not the app.** RLS is enabled in the same migration that creates each table, before any policy exists (deny-all window is never open). See `supabase/migrations/0001_core_schema.sql:214-219`.
- **Hybrid DB access.** User request paths use the requester's JWT so RLS enforces isolation; only worker and migrations use `service_role` (BYPASSRLS). `checklists.json > decisions.db_access`.
- **Composite FKs carry the tenant.** `raw_sources` and `wiki_pages` have `(id, workspace_id)` UNIQUE so child tables use composite FKs — a worker that bypasses RLS still cannot cross tenants (`supabase/migrations/0002_search_schema.sql:45-49`).
- **Korean lexical search is an application concern.** `search_tsv` is deliberately NOT a generated column; the app writes bigram-tokenized `to_tsvector('simple', ...)` values, and `tsv_tokenizer_version` records which tokenizer produced each row.
- **Queue state transitions only through functions.** `jobs` must never be UPDATEd directly; attempt accounting and lock-consistency CHECKs live inside the four SECURITY INVOKER functions, all revoked from `anon`/`authenticated`.

## Layers

**Layer 1 — Immutable sources:** [IMPLEMENTED]
- Purpose: preserve original material verbatim; the "raw source" half of dual citation
- Location: `public.raw_sources`, `public.source_chunks` (`supabase/migrations/0001_core_schema.sql:90`, `0002_search_schema.sql:58`)
- Contains: extracted plain text, `content_hash` idempotency key, `storage_path` to the original file, chunk slices with `char_start`/`char_end`
- Depends on: `workspaces`
- Used by: search channels 2 and 4, dual citation payloads
- Constraint: **no UPDATE policy exists** — immutability is enforced by the absence of a policy, not by convention

**Layer 2 — Compiled wiki:** [IMPLEMENTED]
- Purpose: LLM-compiled, human-verifiable knowledge pages
- Location: `public.wiki_pages`, `public.wiki_embeddings`, `public.wiki_links`
- Contains: slug/title/category/content, quality flags (`explored`, `confidence`, `verification_status`, `disputed`), source backreferences
- Depends on: Layer 1
- Used by: search channels 1, 3, 5; the wiki viewer and canvas

**Queue layer:** [IMPLEMENTED]
- Purpose: decouple ingest requests from long-running LLM work
- Location: `public.jobs` + four functions (`supabase/migrations/0003_jobs.sql`)
- Depends on: `workspaces`
- Used by: ingest API (producer, PLANNED) and worker (consumer, PLANNED)

**Security layer:** [IMPLEMENTED]
- Purpose: tenant isolation and role grading
- Location: `supabase/migrations/0004_rls_policies.sql`
- Contains: `is_workspace_member(uuid)`, `workspace_role(uuid)`, `has_workspace_role(uuid, text)`, `protect_owner_membership()` trigger, 20+ policies

**Application layers (API / worker / UI):** [PLANNED] — see `checklists.json` phases 2 and 3.

## Data Flow

### Read path — question to dual-cited answer [PLANNED, schema IMPLEMENTED]

1. Client sends question with Supabase JWT (`apps/dashboard`)
2. API resolves user and workspace membership (`apps/fastapi-backend/app/auth.py`, `app/deps.py`)
3. Five channels run in parallel (`apps/fastapi-backend/services/hybrid_search.py`):
   1. `wiki_embeddings.embedding` cosine HNSW (`supabase/migrations/0002_search_schema.sql:152`)
   2. `source_chunks.embedding` cosine HNSW (`0002_search_schema.sql:115`)
   3. `wiki_pages.search_tsv` bigram GIN (`0002_search_schema.sql:222`)
   4. `source_chunks.search_tsv` bigram GIN (`0002_search_schema.sql:119`)
   5. `wiki_links` N-hop recursive CTE (`0002_search_schema.sql:198`)
4. RRF fusion, then context assembly with citation anchors `[[wiki:slug]]` / `[[src:chunk_id]]`
5. LLM answer via OpenRouter using an `ask` template from `prompt_templates`
6. Response carries `double_citation: { raw_sources: [...], wiki_pages: [...] }`

### Write path — source to wiki [PLANNED, schema IMPLEMENTED]

1. Upload/URL/text hits the ingest API; original file goes to Storage at `{workspace_id}/{raw_source_id}/{filename}`
2. `raw_sources` row inserted with `content_hash` (dedupe via `unique (workspace_id, content_hash)`)
3. A `jobs` row is enqueued (`status='queued'`, `run_after=now()`)
4. Worker calls `claim_job(worker_id, types[])` — `FOR UPDATE SKIP LOCKED`, increments `attempts` at claim time
5. Parse and chunk → upsert `source_chunks` on `(raw_source_id, chunk_index)`
6. LLM compile → upsert `wiki_pages` on `(workspace_id, slug)`
7. Parse `[[WikiLink]]` → upsert `wiki_links` on `(from_wiki_id, target_slug)`; unresolved targets stay as red links (`to_wiki_id IS NULL`)
8. Embed → upsert `wiki_embeddings` on `(wiki_id, chunk_index)`
9. `complete_job(job_id)` or `fail_job(...)` (backoff → `failed`, exhausted → `dead`)

### Job state machine [IMPLEMENTED]

```text
  queued ──claim──> running ──complete──> succeeded
    ^                  │
    │                  ├──fail (attempts < max)──> failed ──run_after 경과──┐
    │                  └──fail (attempts >= max)──> dead                    │
    └────────────────────────── reap (lock timeout) ────────────────────────┘
```

`failed` is a retry-pending state, not terminal. `dead` is the only human-intervention terminal state.

**State Management:**
- All durable state is Postgres. There is no cache, queue broker, or graph store.
- Job progress is surfaced directly to the frontend by reading `jobs` (members have SELECT only).

## Key Abstractions

**Workspace:**
- Purpose: the tenancy root; every domain table carries `workspace_id`
- Files: `supabase/migrations/0001_core_schema.sql:32-84`
- Pattern: `workspaces.owner_id` + `workspace_members(workspace_id, user_id, role)`; an AFTER INSERT trigger auto-registers the owner as a member so a zero-member (permanently invisible) workspace cannot exist

**Membership helpers:**
- Purpose: break RLS infinite recursion (`42P17`) on `workspace_members`
- Files: `supabase/migrations/0004_rls_policies.sql:44-95`
- Pattern: `security definer stable set search_path = public`; each returns only the caller's own membership (`auth.uid()` is fixed inside), so granting to `authenticated` is safe

**Queue functions:**
- Purpose: the only sanctioned way to mutate `jobs`
- Files: `supabase/migrations/0003_jobs.sql:103-212`
- Pattern: `claim_job(worker_id, types[])`, `complete_job(job_id)`, `fail_job(job_id, error, backoff, max_backoff)`, `reap_stale_jobs(timeout)` — all `service_role`-only

**Red link:**
- Purpose: an outbound wiki link to a page that does not exist yet; doubles as the "next page to write" backlog
- Files: `supabase/migrations/0002_search_schema.sql:163-209`
- Pattern: `to_wiki_id IS NULL`, `resolved` is a stored generated column, target deletion uses `on delete set null (to_wiki_id)` so links revert to red instead of nulling `workspace_id`

**Prompt template:**
- Purpose: swappable compile/ask prompts, global (`workspace_id IS NULL`) or per-workspace
- Files: `supabase/migrations/0001_core_schema.sql:180-204`, `0006_seed_prompts.sql`
- Pattern: `{{variable}}` double-brace placeholders; exactly one default per `target_type` enforced by partial unique indexes

## Entry Points

**Migrations (IMPLEMENTED):**
- Location: `supabase/migrations/`
- Triggers: `supabase db reset` / `supabase db push`
- Order: `0001` → `0002` → `0003` → `0004` → (`0005` reserved) → `0006`

**Local stack (IMPLEMENTED):**
- Location: `supabase/config.toml`
- Ports: API 54421, DB 54422, Studio 54423, Inbucket 54424, Analytics 54427, Pooler 54429, shadow DB 54420 — **not** the Supabase defaults, because another project (`zettlink`) holds 5432x on this machine

**API entrypoint (PLANNED):** `apps/fastapi-backend/main.py` (uvicorn, `/health`, `/docs`)
**Worker entrypoint (PLANNED):** `apps/fastapi-backend/worker.py` (poll loop, SIGTERM graceful shutdown)
**Dashboard (PLANNED):** `apps/dashboard/` (Next.js 15 App Router)

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

**What happens:** Convenience code reaches for the `service_role` client inside an HTTP handler.
**Why it's wrong:** `service_role` is BYPASSRLS. Every policy in `supabase/migrations/0004_rls_policies.sql` (38 verified isolation cases) becomes decorative, and one missing `workspace_id` filter leaks another tenant's data.
**Do this instead:** Inject `user_client(access_token)` into routers; treat any `service_client()` use outside `worker.py` as a reviewable exception. Keep the two factories in separate files (`apps/fastapi-backend/app/db.py`).

### UPDATEing `jobs` directly

**What happens:** Worker code writes `update jobs set status='succeeded'`.
**Why it's wrong:** `attempts` accounting and the `jobs_lock_consistency` CHECK (running ⇒ lock present, otherwise lock NULL) live inside the queue functions. Direct writes desync retry counts and strand locks.
**Do this instead:** Call `complete_job` / `fail_job` / `reap_stale_jobs` (`supabase/migrations/0003_jobs.sql:134-212`).

### Feeding a bigram string to `to_tsquery`

**What happens:** `to_tsquery('simple', bigram(q))` on `"한국어"` produces `"한국 국어"` and raises a syntax error.
**Why it's wrong:** Space-joined bigrams are not valid tsquery syntax; `plainto_tsquery` "fixes" it with `&`, which loses adjacency and admits out-of-order false positives.
**Do this instead:** `phraseto_tsquery('simple', bigram(q))` — bigrams are joined with `<->`, preserving substring semantics.

### Making `search_tsv` a generated column

**What happens:** `search_tsv tsvector generated always as (to_tsvector('simple', content)) stored`.
**Why it's wrong:** Postgres has no Korean morphological analyzer; it splits on whitespace only, which makes lexical search effectively useless for Korean. See `supabase/migrations/0002_search_schema.sql:79-83`.
**Do this instead:** Let the application bigram-tokenize and write `search_tsv` plus `tsv_tokenizer_version`.

### Using `str.format` on prompt templates

**What happens:** Prompt bodies contain markdown, code, and JSON with single braces.
**Why it's wrong:** `str.format` raises `KeyError` or mangles the payload.
**Do this instead:** Plain string replacement on `{{variable}}` (`supabase/migrations/0006_seed_prompts.sql`).

### Assembling LLM context without citation anchors

**What happens:** Chunks are concatenated bare.
**Why it's wrong:** The model has nothing to cite, so dual citation silently collapses to prose.
**Do this instead:** Prefix each wiki chunk with `[[wiki:slug]]` and each source chunk with `[[src:chunk_id]]`.

## Error Handling

**Strategy:** Push invariants into the database; the application maps database outcomes onto HTTP.

**Patterns:**
- CHECK constraints for every enum (`source_type`, `category`, `confidence`, `verification_status`, `role`, `kind`) — job `type` is the one deliberate exception, so the worker must dead-letter unknown types with `last_error`
- Partial unique indexes enforce "exactly one default template per `target_type`"
- Triggers guard structural invariants: `add_owner_as_member`, `protect_owner_membership`
- Retry/dead-letter is a queue concern, with exponential backoff `base * 2^(attempts-1)` capped by `p_max_backoff`
- API mapping (PLANNED): rows affected 0 → 403; `42501` → 403; missing membership → 403; no token → 401

## Cross-Cutting Concerns

**Logging:** Structured logging planned in `apps/fastapi-backend/app/config.py` (P0-INIT-02). Not implemented.
**Validation:** Database CHECK/UNIQUE/FK today; Pydantic models with 3-retry repair for LLM structured output (PLANNED, P2-LLM-01) — enum values in the compile output schema must match the `0001` CHECK strings exactly.
**Authentication:** Supabase Auth (`auth.users`), JWT verified per request; authorization is RLS with graded roles owner(3) > editor(2) > viewer(1).
**Idempotency:** Defined as "re-ingesting the same `content_hash` adds no rows and `(workspace_id, slug)` upsert produces no duplicate wikis" — not "the LLM emits identical text".

---

*Architecture analysis: 2026-08-01*

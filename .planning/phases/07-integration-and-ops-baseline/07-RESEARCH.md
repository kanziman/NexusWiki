# Phase 7: Integration and Ops Baseline - Research

**Researched:** 2026-08-13  
**Domain:** Local-stack integration testing, retrieval baselining, and dashboard operations observability  
**Confidence:** HIGH

## User Constraints

### Locked implementation decisions (copied from `07-CONTEXT.md`)

- **D-01:** The E2E test uses a mocked LLM/embedding provider, never a real OpenRouter call. Postgres stays real.
- **D-02:** Drive real API + worker code through pytest at the API level: `POST /sources → enqueue_source_job → parse → compile → link_sync → embed → search`; no browser/Playwright.
- **D-03:** Fold OPS-02/03/04 suites into the existing pytest PR-gate job, not a separate on-demand job.
- **D-04:** E2E, idempotency, and isolation tests share one minimal fixture set: one file source, one URL source, one text source.
- **D-05:** Put OPS-06 inside the existing workspace Settings page as a tab/panel, never a top-level route.
- **D-06:** Render cost (`usage_events` aggregate versus `workspaces.monthly_budget_micros`) and per-stage queued/running/dead health together.
- **D-07:** Refresh on entry and explicit manual refresh only; never add polling.
- **D-08:** Operations data is visible to owner/editor, never viewer; server authorization remains authoritative.
- **D-09:** Build OPS-04 as a local-Supabase pytest API-level suite covering all 9 tables × SELECT/INSERT/UPDATE/DELETE, job RPCs, and Storage paths. Reuse A(owner/editor/viewer), B(owner), non-member, and anon principals.
- **D-10:** Use free, synthetic 1024-dimension vectors to pad the local corpus to 10^4–10^5 rows.
- **D-11:** Reuse the existing 30–50 multilingual evidence-labelled golden set; synthetic rows only induce a representative HNSW plan.
- **D-12:** Benchmark locally first; escalate to Railway/production-like hardware only if local results are inconclusive.

### Claude's Discretion (copied from `07-CONTEXT.md`)

- Exact OPS-06 panel layout/component structure, reusing the Phase 6 Settings patterns.
- Precise shared pytest fixture-helper API for the minimal sources and 9-table matrix.
- Exact synthetic-vector generation method and corpus-composition ratio.

### Deferred Ideas (copied from `07-CONTEXT.md`)

None.

## Summary

Phase 7 should be additive: use the real local Supabase stack for all persistence, RLS, queue, Storage, and HNSW behaviour, while replacing only the two paid/nondeterministic provider calls at their injection seam. The existing implementation already exposes each needed seam: source POST creates a parse job, workers have `run_*` functions, and the retrieval route accepts a replaceable `app.state.retrieval_service`. [VERIFIED: `apps/api/src/api/routers/sources.py:185-235`, `apps/worker/src/worker/handlers/parse.py:79-88`, `apps/api/src/api/routers/retrieval.py:54-93`]

The highest-leverage layout is three backend test modules sharing one local-only fixture module, one benchmark extension that reuses the checked-in deterministic 50k-row corpus generator, and one API/dashboard feature slice for Operations. No new third-party library is necessary. [VERIFIED: `scripts/generate_retrieval_benchmark_corpus.py:29-35`, `scripts/generate_retrieval_benchmark_corpus.py:145-158`, `apps/dashboard/package.json:15-48`]

**Primary recommendation:** First establish reusable local-stack fixtures and deterministic provider doubles, then implement OPS-02/03/04 as focused integration tests, reuse the existing benchmark runner for OPS-05, and finally add one owner/editor-only Operations snapshot endpoint plus the Settings tab that consumes it.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|---|---|---|---|
| E2E pipeline proof | API / Backend | Database / Storage | HTTP entry, real worker stage functions, queue/RLS/Storage remain real. |
| Re-ingestion shrink proof | API / Backend | Database / Storage | Handler writes must prove upsert-plus-truncate results in no residual rows. |
| Tenant-isolation matrix | Database / Storage | API / Backend | RLS, grants, RPC checks, and Storage policies decide the result; HTTP verifies application use of the requester JWT. |
| Retrieval quality/latency baseline | API / Backend | Database / Storage | `RetrievalService` owns fusion/meta; database owns HNSW execution. |
| Cost/pipeline snapshot | API / Backend | Frontend | API aggregates RLS-scoped persisted facts; Settings renders them without recreating job policy. |

## Standard Stack

### Core

| Library / tool | Existing version | Purpose | Why standard here |
|---|---:|---|---|
| pytest + pytest-asyncio | `9.1.1` / `1.4.0` | API/worker/local-stack tests | Already the root test runner with automatic async mode. [VERIFIED: `pyproject.toml:12-25` — `"pytest==9.1.1"`, `"pytest-asyncio==1.4.0"`, `asyncio_mode = "auto"`] |
| httpx | existing app dependency | Test FastAPI through the existing ASGI client fixture and local Supabase REST/Auth endpoints | Existing fixtures already create isolated real users/workspaces via loopback-only HTTP. [VERIFIED: `apps/api/tests/conftest.py:1-19`, `apps/api/tests/conftest.py:208-228`] |
| Vitest + Testing Library | `4.1.10` / `16.3.2` | Operations panel component tests | Existing dashboard runner and component-test convention. [VERIFIED: `apps/dashboard/package.json:29-48` — `"@testing-library/react": "16.3.2"`, `"vitest": "4.1.10"`] |
| Existing benchmark scripts | repository code | Deterministic vectors, loader, full-path records, comparison | They already validate 1024 dimensions and load 25,000 source + 25,000 wiki vector rows. [VERIFIED: `scripts/generate_retrieval_benchmark_corpus.py:29-35` — `(1024, 25000, 25000)`] |

### Supporting

| Existing component | Use | Guidance |
|---|---|---|
| `apps/api/tests/conftest.py` | Local-only principal creation, cleanup, and API client factories | Extend it; preserve loopback guard and function-scoped cleanup. [VERIFIED: `apps/api/tests/conftest.py:32-42`, `apps/api/tests/conftest.py:208-257`] |
| `SettingsMembersPanel` | 640px Settings shell and client state ownership | Evolve/rename it to a Settings tab-panel wrapper rather than add a route. [VERIFIED: `apps/dashboard/components/SettingsMembersPanel.tsx:21-56`] |
| `apiFetch` | Authenticated dashboard-to-API call and safe error parsing | Use for one Operations snapshot request; never expose raw backend response errors. [VERIFIED: `apps/dashboard/lib/api-client.ts:48-104`, `apps/dashboard/lib/api-client.ts:106-132`] |
| `scripts/benchmark_retrieval.py` | Append-only full-path quality and latency record | Reuse the `RetrievalService` runner and record comparator; do not build a separate benchmark. [VERIFIED: `scripts/benchmark_retrieval.py:17-29`, `scripts/benchmark_retrieval.py:93-110`] |

**Installation:** none. This phase should not change dependencies.  
**Package legitimacy audit:** not applicable — no external packages recommended.

## Architecture Patterns

### System Architecture

```text
pytest local-stack fixture
  ├─ real user JWT ─> POST /workspaces/{id}/sources/{text,file,url}
  │                    └─ raw_sources + enqueue_source_job (real Supabase)
  ├─ deterministic LLM/embed doubles ─> run_parse → run_compile → run_link_sync → run_embed
  │                                      └─ real ServiceDb / queue / RLS / Storage
  ├─ real user JWT ─> POST /workspaces/{id}/retrieval
  │                    └─ RetrievalService → 4 RPC channels → RRF/meta
  └─ assertions: rows, job states, evidence identity, tenant boundaries

Settings Operations tab
  └─ apiFetch GET /workspaces/{id}/operations (owner/editor)
       └─ RLS-scoped budget aggregate + stage counts
            └─ last successful snapshot retained on manual-refresh error
```

### Pattern 1: Split deterministic provider doubles from real persistence

**Use:** Monkeypatch/inject the OpenRouter and embedding boundary only, then invoke the existing `run_parse`, `run_compile`, `run_link_sync`, and `run_embed` functions against a real `ServiceDb` where feasible. The run functions are explicitly structured as injectable units; `handle_*` wrappers own settings and network clients. [VERIFIED: `apps/worker/src/worker/handlers/parse.py:54-88`, `apps/worker/src/worker/handlers/compile.py:82-104`, `apps/worker/src/worker/handlers/embed.py:17-25`]

**Why:** Mocking Postgres would not verify the Phase 7 properties. The local fixture intentionally uses the loopback stack and skips when unavailable, preventing accidental cloud mutation. [VERIFIED: `apps/api/tests/conftest.py:208-228`]

**Plan shape:** create `apps/api/tests/fixtures/pipeline.py` (or equivalent) with:

1. Three unique sources: text, local text/PDF-compatible file fixture, and a URL served by an in-process `httpx.MockTransport` only for fetch content.
2. A queue-drain helper that claims/dispatches the staged jobs through real queue RPCs; it must never mutate `public.jobs` directly.
3. Deterministic compile payload and 1024-float embedding result shared by E2E/idempotency tests.
4. Row-count/read helpers scoped by `workspace_id` and `raw_source_id`.

### Pattern 2: Assert state transitions and row deltas, not generated prose

**Use:** OPS-02 asserts source/chunk/page/link/embedding counts, terminal job states, and retrieval evidence. OPS-03 runs a first long text then a shorter text through the parse/reprocess path and asserts `source_chunks` contains exactly contiguous indexes for the shortened output, with no index at or above the new count. [VERIFIED: `apps/worker/src/worker/db/service.py:321-337`, `apps/worker/src/worker/handlers/parse.py:8-15`]

**Why:** `delete_source_chunks_from()` is the explicit shrink protection. Quote: `"chunk_index": f"gte.{from_index}"`; a same-size re-run cannot exercise that branch. [VERIFIED: `apps/worker/src/worker/db/service.py:321-337`]

### Pattern 3: Table-driven isolation with allowed-success controls

**Use:** Model each table/path as an entry containing normal owner action, cross-workspace action, expected shape (`[]`, `403`, or SQLSTATE), and any immutable/derived-table exception. Run both directions and include an allowed own-workspace control so “deny everything” cannot pass. The existing Phase 2 suite already uses exactly this bidirectional/control discipline. [VERIFIED: `apps/api/tests/test_workspaces_isolation.py:35-97`, `apps/api/tests/test_workspaces_isolation.py:127-190`]

**Nine tables:** `workspaces`, `workspace_members`, `raw_sources`, `wiki_pages`, `source_chunks`, `wiki_embeddings`, `wiki_links`, `prompt_templates`, and `jobs`; `usage_events` is an additional OPS-06 read surface, not a substitute for the nine-table contract. The authenticated grants are explicit and must drive the action matrix. [VERIFIED: `supabase/migrations/0007_search_and_queue_extensions.sql:353-371` — the quoted table list and grants; `supabase/migrations/0009_pipeline_ops.sql:112-145` — `usage_events` and member SELECT policy]

### Pattern 4: Reuse the canonical benchmark corpus; preserve policy defaults

**Use:** Run the existing deterministic corpus generator and full-path benchmark at the canonical baseline scale of 25,000 source vectors plus 25,000 wiki vectors (50,000 total). It already:

- fixes the vector dimension at 1024;
- inserts labelled evidence first, then nonmatching decoys;
- creates 25,000 source and 25,000 wiki vector rows;
- runs `ANALYZE` after insertion; and
- scopes cleanup to the single deterministic workspace. [VERIFIED: `scripts/generate_retrieval_benchmark_corpus.py:102-158`]

The benchmark must invoke `RetrievalService.retrieve()` for each unchanged gold query, capture `meta` envelopes, persist an append-only record, and report per-channel latency from those envelopes plus overall `elapsed_ms`. Retrieval already emits `requested_k`, `returned`, `underfill`, `elapsed_ms`, and channel envelopes. Scale above the canonical 50,000 total vectors only when the appended local `EXPLAIN` evidence still does not select a representative HNSW plan; preserve corpus/manifest/policy/revision pins so the new evidence is not compared to the canonical arms. [VERIFIED: `apps/api/src/api/services/retrieval.py:82-170`]

Do not alter `strict_order`, `graph_enabled`, weights, k, or limits in this phase. A result can only propose a later policy change through the existing policy log gate. [VERIFIED: `docs/ops/hnsw-order-benchmark.md:7-13`, `docs/ops/hnsw-order-benchmark.md:116-131`]

### Pattern 5: One server-owned Operations snapshot contract

**Use:** Add a single API endpoint (recommended `GET /workspaces/{workspace_id}/operations`) that does all authorization and aggregation once, returning a stable DTO:

```json
{
  "budget": {"cap_micros": 0, "spent_micros": 0, "remaining_micros": 0, "month_start": "…", "truncated": false, "authoritative": false},
  "pipeline": [{"type": "parse", "step_label": "원문 파싱", "queued": 0, "running": 0, "dead": 0}],
  "observed_at": "…"
}
```

The literals above are derived from existing source-of-truth values: `CHAIN_ORDER = ("parse", "compile", "link_sync", "embed", "conflict_check")` and `STEP_LABELS` maps them to the five Korean labels. [VERIFIED: `apps/api/src/api/routers/jobs.py:27-40` — `"parse", "compile", "link_sync", "embed", "conflict_check"` and labels] The budget object should reuse the current calculation semantics: at most 1,000 events, first day of the UTC month, and `authoritative: False`. [VERIFIED: `apps/api/src/api/routers/jobs.py:87-110`, `apps/api/src/api/routers/jobs.py:177-200`]

Authorize `editor` and `owner` in the server before returning the aggregate. Build this snapshot through direct requester-JWT, RLS-scoped `UserDb` reads and aggregates, using the fixed server-owned stage list to construct the DTO. First probe this exact direct path in router tests. Only if those tests demonstrate that PostgREST cannot technically provide the exact DTO, add one narrow `SECURITY INVOKER` RPC with explicit workspace membership enforcement and a fixed return schema; do not create that migration proactively. The dashboard's conditional tab is defense in depth only. Avoid returning job payload, `last_error`, usage metadata, provider/model, or raw error text; the existing job response already demonstrates an intentional UI contract rather than direct row exposure. [VERIFIED: `apps/api/src/api/routers/jobs.py:58-79`]

## Recommended File-Level Plan

| Requirement | Primary files | Test/evidence files | Dependency |
|---|---|---|---|
| OPS-02 | new API integration test plus reusable fixture module; existing source router and worker handlers unchanged unless testability gap is discovered | `apps/api/tests/test_pipeline_e2e.py` | shared fixture first |
| OPS-03 | `apps/worker/src/worker/db/service.py` only if a real-test seam is missing | `apps/api/tests/test_reingestion_idempotency.py` | shared fixture + parse path |
| OPS-04 | extend `conftest.py` only with principal helpers and consume `apps/api/tests/fixtures/pipeline.py`; keep Phase 2 test intact | `apps/api/tests/test_tenant_isolation_full_path.py` | Plan 07-01 shared file/URL/text fixture, then principal/matrix helpers |
| OPS-05 | `scripts/benchmark_retrieval.py`, benchmark docs/records only if result schema lacks per-channel percentile summary | `packages/core/tests/test_retrieval_golden.py`, append-only `docs/ops/benchmark-records/*`, `docs/ops/hnsw-order-benchmark.md` | local Docker/Supabase |
| OPS-06 | `apps/api/src/api/routers/jobs.py`, router tests, Settings panel/page and dashboard tests | `apps/api/tests/test_jobs_router.py`, `apps/dashboard/tests/OperationsPanel.test.tsx` | API DTO before UI |

## Common Pitfalls

### Do not make CI green by skipping the actual proof

The current PR pytest job intentionally has no Supabase stack and prints skipped DB tests using `-rs`; local-stack tests must remain in that job but its authoritative execution is `supabase start` followed by the full suite locally. Do not add secrets or Cloud credentials to CI. [VERIFIED: `.github/workflows/ci.yml:138-171`]

### Do not direct-update `jobs`

Queue state and accounting live in queue RPCs. E2E drain code must claim/complete/fail through the existing queue protocol, never `UPDATE public.jobs`; otherwise it bypasses lock-consistency and attempts accounting. [VERIFIED: `supabase/migrations/0009_pipeline_ops.sql:300-336` — `enqueue_source_job` owns user enqueue and returns the existing pending job]

### Distinguish silent RLS outcomes

Read paths can validly return zero rows while a write denied by a `USING` policy can also return zero affected rows; a `WITH CHECK`/definer denial is SQLSTATE `42501`. The matrix must assert the expected shape, not merely “no exception.” The existing suite distinguishes empty reads from API 403 write mappings. [VERIFIED: `apps/api/tests/test_workspaces_isolation.py:99-190`]

### Keep the API’s user JWT boundary

API routes must use `UserDb` with `credentials.credentials`; importing `worker.db.service` into API would introduce a service-role/BYPASSRLS path. [VERIFIED: `apps/api/src/api/routers/sources.py:114-138`; `pyproject.toml:38-49`]

### Preserve Storage safety in the shared file fixture

Use only workspace-prefixed paths produced by the existing API and assert foreign-path access is rejected; never hand-construct a foreign path as service role. The parse worker rejects a file source whose first Storage path segment differs from `workspace_id`. [VERIFIED: `apps/worker/src/worker/handlers/parse.py:106-124`]

### Benchmark comparability is more important than a fast number

Use fresh load/cleanup per arm, identical corpus/golden/manifest/generator/policy/git revision pins, repeat count, and append-only output. The previous invalid v4 strict/relaxed pair proves that comparing differing revisions yields misleading evidence. [VERIFIED: `docs/ops/hnsw-order-benchmark.md:49-89`]

### Respect the established Tailwind width collision workaround

The Settings column must retain `style={{ maxWidth: "640px" }}` rather than `max-w-xl`; project tokens make the latter resolve incorrectly. [VERIFIED: `apps/dashboard/components/SettingsMembersPanel.tsx:27-35` — `style={{ maxWidth: "640px" }}`]

## Validation Architecture

| Property | Value |
|---|---|
| Backend framework | pytest 9.1.1 + pytest-asyncio 1.4.0 [VERIFIED: `pyproject.toml:12-25`] |
| Frontend framework | Vitest 4.1.10 + Testing Library [VERIFIED: `apps/dashboard/package.json:29-48`] |
| Quick backend run | `UV_CACHE_DIR=/tmp/nexuswiki-uv-cache uv run pytest -q apps/api/tests/test_pipeline_e2e.py apps/api/tests/test_reingestion_idempotency.py apps/api/tests/test_tenant_isolation_full_path.py apps/api/tests/test_jobs_router.py` |
| Full backend run | `UV_CACHE_DIR=/tmp/nexuswiki-uv-cache uv run pytest -rs` [VERIFIED: `.github/workflows/ci.yml:167-171`] |
| Dashboard run | `pnpm --dir apps/dashboard test && pnpm --dir apps/dashboard typecheck` [VERIFIED: `apps/dashboard/package.json:6-13`] |

| Req ID | Behaviour | Test/evidence | Automated command |
|---|---|---|---|
| OPS-02 | Empty workspace proceeds source POST → job stages → retrieval with evidence | local-stack pytest integration | focused pytest above |
| OPS-03 | duplicate hash adds no rows; shorter reprocess removes trailing chunks/embeddings | local-stack pytest integration | focused pytest above |
| OPS-04 | all table/API/job/Storage cross-tenant paths deny or hide correctly, with positive control | local-stack pytest integration | focused pytest above |
| OPS-05 | unchanged gold set runs at HNSW-forcing scale; records quality + per-channel/overall latency | benchmark record + comparator | `uv run python scripts/benchmark_retrieval.py …` plus existing comparator |
| OPS-06 | owner/editor snapshot works; viewer API/tab denied/absent; loading/error/manual refresh states render | API + Vitest | focused pytest + dashboard commands |

**Sampling:** run focused tests per task, root pytest and dashboard tests at wave merge, then run local `supabase start` plus the root suite before phase verification. Use `-rs` so skipped database tests are visible. [VERIFIED: `.github/workflows/ci.yml:155-171`]

## Security Domain

| ASVS L1 category | Applies | Required control |
|---|---|---|
| V2 Authentication | Yes | API request uses bearer JWT; unauthenticated operations endpoint returns 401. |
| V3 Session management | Yes | Dashboard uses the existing `apiFetch`, which obtains the current session per call rather than caching a token. [VERIFIED: `apps/dashboard/lib/api-client.ts:39-62`] |
| V4 Access control | Yes | RLS-backed UserDb, owner/editor server gate, full cross-tenant matrix, storage path coverage. |
| V5 Input validation | Yes | Strict Pydantic DTOs and fixed server-owned stage labels; no client-supplied status/type aggregation. |
| V8 Data protection | Yes | Never expose payloads, errors, source text, LLM response metadata, or provider/model details in Operations. [VERIFIED: `supabase/migrations/0009_pipeline_ops.sql:135-145`] |

## Assumptions Log

| # | Claim | Risk if wrong |
|---|---|---|
| A1 | The new Operations endpoint uses direct requester-JWT, RLS-scoped UserDb reads/aggregates and a fixed server-owned stage list. | Router tests must first prove that path returns the exact DTO; only a demonstrated PostgREST technical limitation permits one narrow `SECURITY INVOKER` RPC, never client-side aggregation. |
| A2 | A Phase 7-specific local-stack queue-drain helper can invoke the worker handler sequence without starting a long-lived worker process. | If queue dispatch has a non-injectable seam, extract a small dispatcher helper from the worker loop while preserving production behaviour. |

## Open Questions (RESOLVED)

1. **Canonical corpus scale:** use the existing deterministic 25,000-source plus 25,000-wiki-vector corpus (50,000 total) and run `ANALYZE`. Escalate scale only if the Phase-7 append-only local `EXPLAIN` evidence still fails to choose representative HNSW, preserving distinct comparable pins for any escalation record. [VERIFIED: `scripts/generate_retrieval_benchmark_corpus.py:145-158`]

2. **Operations aggregation:** use direct requester-JWT, RLS-scoped `UserDb` reads/aggregates with a fixed server-owned five-stage list. Probe that exact DTO in router tests before implementation completion. A narrow `SECURITY INVOKER` RPC is an explicit contingency only if those tests prove PostgREST aggregation technically cannot satisfy the DTO; do not add a migration proactively. [VERIFIED: `apps/api/src/api/routers/jobs.py:87-105`, `apps/api/src/api/routers/jobs.py:177-200`]

## Sources

### Primary

- Repository source-of-truth files cited inline: phase context/UI contract, API/worker sources, migrations, CI workflow, test fixtures, benchmark scripts, and HNSW decision record.

### External

- None required: Phase 7 needs no dependency adoption and is governed by existing repository contracts.

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH — every recommended tool is already pinned in the repository.
- Architecture: HIGH — all seams and contracts were read in source this session.
- Pitfalls: HIGH — derived from existing test/workflow/migration comments and recorded benchmark evidence.

**Research date:** 2026-08-13  
**Valid until:** 2026-09-12

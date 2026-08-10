# Phase 4 Pattern Mapping — Hybrid Retrieval and Fusion

## Read first

1. `.planning/phases/04-hybrid-retrieval-and-fusion/04-CONTEXT.md` and `04-RESEARCH.md` — locked scope, policy ownership, and the query-embedding decision gate.
2. `.planning/REQUIREMENTS.md` — `RTV-01` through `RTV-09`; `.planning/PROJECT.md` constraints.
3. `supabase/migrations/0007_search_and_queue_extensions.sql` and `0008_embedding_dimension.sql` — source dense-search/RLS/HNSW/ACL contract.
4. `supabase/migrations/0002_search_schema.sql` — physical five-channel tables and indexes.
5. `packages/core/src/nexuswiki_core/tokenizer.py` — required normalization-before-bigram contract.
6. `apps/api/src/api/db/user.py`, `apps/api/src/api/routers/jobs.py`, `apps/api/src/api/main.py` — API dependency/router patterns.
7. `apps/worker/src/worker/embedding.py`, `handlers/embed.py`, `__main__.py`, and `settings.py` — provider and process ownership.
8. `supabase/tests/0008_search_contract.sql`, `scripts/verify_search_contract.sh`, `scripts/ci_check_search_contract.sh`, `apps/api/tests/conftest.py` — real DB and API test conventions.

## Expected files and closest analogs

| Likely file | Role / data flow | Closest analog and concrete convention |
|---|---|---|
| `supabase/migrations/0011_retrieval.sql` | DB boundary: lexical materialization/indexing, wiki dense + both lexical RPCs, bounded graph RPC, grants/revokes, schema reload. API -> requester JWT -> RPC -> RLS-filtered rows. | `0008_embedding_dimension.sql::search_chunks`. New search functions must be `language sql security invoker stable`, `set search_path = public`, and vector functions must retain `hnsw.iterative_scan`, `hnsw.ef_search`, `hnsw.max_scan_tuples`, and `operator(extensions.<=>)`. Never place RRF weights, final k, or graph policy in SQL. |
| `supabase/tests/0011_retrieval_contract.sql` | Transactional DB contract: catalog, ACL, RLS-safe behavior, lexical result shape/version filtering, bounded/cycle-safe graph, vector dimensions and HNSW plan assertion. | `supabase/tests/0008_search_contract.sql`: `begin;` fixed UUID fixtures; `do $t$ ... raise exception ... end $t$;`; end with explicit success marker then `rollback;`. |
| `scripts/verify_retrieval_contract.sh`, `scripts/ci_check_retrieval_contract.sh` (or extend existing search scripts) | Local Docker/psql execution plus source-level CI safety net. | Existing scripts use `set -euo pipefail`, capture output before returning failure, require a final `...: ok` marker, and inspect the last defining migration after stripping SQL comments. |
| `packages/core/src/nexuswiki_core/retrieval_policy.py` | Immutable versioned policy: `POLICY_VERSION`, equal initial first-wave weights, RRF k, over-fetch/final k, graph limits and default-off flag. Policy stamped on retrieval/benchmark records. | `tokenizer.py` is the model for a small pure contract module with explicit typed constants, public exports, and strong comments around silent correctness failures. |
| `packages/core/src/nexuswiki_core/rrf.py` (or policy module) | Pure evidence DTO, canonical dedupe key, rank-only RRF, deterministic tie break, graph-rank derivation/re-fusion. No HTTP/DB imports. | `nexuswiki_core/slug.py`/`tokenizer.py` pure-function style. Use rank `1`-based and score `weight / (rrf_k + rank)`; accumulate `channels`, retain selected wiki embedding metadata, and tie-break canonical identity. |
| `packages/core/tests/test_retrieval_policy.py`, `test_rrf.py` | Unit tests for version invariants, rank math, equal weights, dedupe, contribution attribution, deterministic ties, graph disabled/enabled behavior. | `packages/core/tests/test_tokenizer.py` has direct, small behavioral assertions and uses no external service. |
| `apps/api/src/api/services/retrieval.py` plus `__init__.py` | Orchestration: normalize+bigram once; acquire one query vector; run four named channels concurrently with `asyncio.gather(..., return_exceptions=True)`; isolate malformed payload/errors; RRF; optional graph then re-fuse. | `api/db/user.py::UserDb.rpc(function, params=...)` is the only user-path DB transport. Preserve `asyncio.CancelledError`; a channel failure yields metadata, not a failed request. |
| `apps/api/src/api/routers/retrieval.py`, `apps/api/src/api/main.py` | Thin authenticated endpoint / DTO adapter, uses per-request `UserDb`, passes `workspace_id`, returns retrieval evidence plus `meta`; no answer generation/SSE/citation anchors (Phase 5). | `routers/jobs.py`: `_bearer = HTTPBearer()`, `_user_db(request, credentials)`, `UUID` path params, and response shaping owned by router instead of exposing internal data. Register via `app.include_router(...)`. |
| `apps/api/src/api/settings.py`, settings tests | API may hold an internal worker embedding-service URL and safe operational bounds only. | `ApiSettings` explicitly forbids `OPENROUTER_API_KEY`, service key, and DB URL. Add any new field to the allow-list assertion in `packages/core/tests/test_settings.py`; never add provider secret. |
| `apps/worker/src/worker/query_embedding.py` / private endpoint module; `worker/__main__.py`; `worker/settings.py` | Required decision-gated secret-safe query-vector service. API sends bounded text over private network; worker calls existing embedding adapter and returns validated vector only; no service-role DB path. | `embedding.py::embed_texts(client, *, settings, texts)` validates provider and enforces `EMBEDDING_DIMENSIONS = 1024`. Worker `main()` owns `WorkerSettings`, signals, and lifecycle; supervise queue and private server with graceful shutdown. |
| `apps/api/tests/test_retrieval*.py` | Mock-transport unit/route tests: JWT RPC calls, no service client, policy metadata, degraded success, bad RPC payload, cancellation propagation. | `test_jobs_router.py` and `test_sources_router.py` fixture/app injection approach; `UserDb` is injected through the request app state. |
| `apps/api/tests/test_retrieval_integration.py` | Real local Supabase test of tenant isolation, ACL/RPC result visibility, and realistic seeded retrieval path. | `tests/conftest.py::two_workspaces_two_users`: unique tenant actors, loopback-only guard, skip when local stack absent. Never reuse admin/service credentials for the request path under test. |
| `packages/core/tests/fixtures/retrieval/golden_queries.v1.json`, representative corpus fixture, provenance README, benchmark runner/tests | Version-pinned 30–50 Korean/English/mixed real-scenario evidence labels; runner emits corpus/golden hashes, policy version, git SHA, metrics and order-mode comparison. | Existing test fixtures are repository-owned and deterministic. Each gold row needs stable id, language, query, corpus version, k, required source/wiki evidence, alternatives, and max rank. |

## Essential existing signatures / excerpts

### Requester-safe RPC transport

`apps/api/src/api/db/user.py`:

```python
async def rpc(self, function: str, *, params: Mapping[str, Any]) -> list[dict[str, Any]]:
    response = await self._client.post(
        f"{self._base_url}/rpc/{function}", json=dict(params), headers=self._headers
    )
```

Headers contain the publishable key and `Authorization: Bearer <requester JWT>`. `UserDb` deliberately does not impose workspace filtering itself: SQL/RLS is authoritative. Retrieval should still pass and filter by the route workspace id as defense-in-depth, never use `worker.db.service`.

### Canonical lexical contract

`packages/core/src/nexuswiki_core/tokenizer.py`:

```python
def bigram(normalized: str) -> str:
    if not is_normalized(normalized):
        raise ValueError("bigram()은 정규화된 입력만 받는다 ...")
```

All indexing and query paths must call `bigram(normalize(text))`, persist/check `TSV_TOKENIZER_VERSION`, and use SQL `to_tsvector('simple', p_bigrams)` / `phraseto_tsquery('simple', p_bigrams)`. Do not construct `tsvector` textual encodings in PostgREST.

### Vector search/RLS/HNSW reference

`supabase/migrations/0008_embedding_dimension.sql` defines:

```sql
create or replace function public.search_chunks(
  p_workspace_id uuid, p_query extensions.vector(1024), p_k int default 20
) returns table (...) language sql security invoker stable
set search_path = public
set hnsw.iterative_scan = 'strict_order'
set hnsw.ef_search = '200'
set hnsw.max_scan_tuples = '40000'
as $$
  select ... from public.source_chunks c
  where c.workspace_id = p_workspace_id and c.embedding is not null
  order by c.embedding operator(extensions.<=>) p_query limit p_k;
$$;
revoke all on function public.search_chunks(uuid, extensions.vector, int) from public, anon;
grant execute on function public.search_chunks(uuid, extensions.vector, int) to authenticated;
```

New/replaced RPCs need corresponding explicit revokes from `public`, `anon`, and `service_role`, grant only `authenticated`, then `notify pgrst, 'reload schema'`. Workspace predicates are necessary but not a substitute for `SECURITY INVOKER` + RLS.

### Existing schema constraints

- `source_chunks`: canonical source evidence id; `workspace_id`, `raw_source_id`, `chunk_index`, `content`, `embedding`, `search_tsv`, tokenizer version; HNSW and GIN indexes.
- `wiki_embeddings`: chunk-level dense rows with `wiki_id`, `workspace_id`, `chunk_index`, `content`, and `embedding`.
- `wiki_pages`: canonical wiki presentation/evidence id, `search_tsv`, tokenizer version, GIN index.
- `wiki_links`: only resolved edges (`to_wiki_id is not null`) may be traversed; indexes are `(workspace_id, from_wiki_id)` and partial `(workspace_id, to_wiki_id)`.

Graph SQL must accept fused seed UUIDs only; constrain workspace in anchor and recursive terms, cap depth `<= 2`, per-frontier fan-out and total rows in SQL, carry UUID path and reject cycles. Python policy limits are user-tunable; SQL caps are a DoS backstop.

### Embedding secret/process boundary

`apps/worker/src/worker/embedding.py`:

```python
async def embed_texts(client, *, settings: WorkerSettings, texts: list[str]) -> EmbeddingResult:
    ...
    if any(len(v) != EMBEDDING_DIMENSIONS for v in vectors):
        raise ValueError("embedding_dimension_mismatch")
```

`ApiSettings` must never contain `OPENROUTER_API_KEY`; only `WorkerSettings` does. The required architecture checkpoint precedes adding a worker-private query embedding service (or a demonstrably equivalent secret-safe boundary), with request size/timeout/rate/cost bounds and fake-client injection for tests.

## Test and observability requirements

- Test every channel adapter independently, four-way concurrency, shared-vector failure degrading both vector channels while lexical stays live, any single RPC failure, malformed payload, underfill (`returned < requested_k`), and no swallowing cancellation.
- Return/record per-channel status (`ok`, `failed`, `disabled`), elapsed time, requested/returned counts, safe error category, raw hit ids, contribution counts, and policy/corpus/golden version plus git SHA. Graph default-off is `disabled`, never `failed`.
- Golden evaluation pass predicate: each required evidence unit is within query top-k and at/better than its recorded rank threshold; explicitly allowed alternatives are the only substitutes. Report recall@k, strict query pass rate, rank/MRR, contribution rate, p50/p95 channel/total latency, underfill rate, and graph-on/off delta.
- Benchmark `strict_order` and `relaxed_order` on the same pinned corpus/golden/policy. Select or alter policy only with recorded before/after evidence; policy changes are **costly** and must preserve reproducibility.
- HNSW `EXPLAIN` must be tested with a corpus/selectivity condition sufficient to make an index plan meaningful; tiny fixtures cannot establish this.

## Scope fences

- Do not add an answer/SSE endpoint, citation anchors/intersection, dashboard UI, or a graph DB; those are later phases.
- Do not use SQL fusion or SQL-owned tuneables; physical retrieval safety belongs in SQL, deterministic policy/fusion belongs in Python.
- Do not expose service role, provider keys, raw provider errors, unbounded graph traversal, or cross-workspace evidence.

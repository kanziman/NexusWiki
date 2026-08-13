# Phase 4 Research: Hybrid Retrieval and Fusion

**Phase:** 4 — Hybrid Retrieval and Fusion  
**Researched:** 2026-08-11  
**Status:** Ready to plan, with one architecture decision gate described below

## Executive Summary

Phase 4 should be planned as a tracer-first retrieval vertical slice, then expanded around it:

1. Make every physical retrieval channel callable through RLS-preserving RPCs and make the two lexical indexes actually populated.
2. Add a pure, versioned Python retrieval policy and rank-only RRF implementation with a stable evidence identity model.
3. Build the four-channel concurrent first wave with per-channel failure isolation, then the bounded, default-off graph second wave and re-fusion.
4. Establish the version-pinned corpus, 30–50 evidence-labelled golden queries, benchmark runner and HNSW-order decision record before tuning defaults.
5. Close the phase with real-DB contracts: HNSW `EXPLAIN` assertions, RLS/isolation coverage, underfill/contribution telemetry, and a reproducible benchmark record.

The core unresolved integration is **query embedding**. `ApiSettings` deliberately cannot carry `OPENROUTER_API_KEY`, while all vector channels need a synchronous query vector. Existing `worker.embedding.embed_texts()` is correct but only usable with `WorkerSettings`. The phase must introduce a narrow worker-owned/internal query-embedding boundary (recommended) or explicitly approve an equivalent secret-safe boundary before the retrieval endpoint is planned. Do not add OpenRouter credentials to `ApiSettings`; that violates SEC-01.

## Confirmed Existing Foundation

### Physical five-channel model

`supabase/migrations/0002_search_schema.sql` already defines the intended channels:

| Channel | Relation / index | Current operational state |
|---|---|---|
| 1 wiki dense | `wiki_embeddings.embedding`, `wiki_embeddings_embedding_idx` HNSW | embeddings exist after Phase 3; no user RPC yet |
| 2 source dense | `source_chunks.embedding`, `source_chunks_embedding_idx` HNSW | `public.search_chunks()` exists and is authenticated/RLS-safe |
| 3 wiki lexical | `wiki_pages.search_tsv`, `wiki_pages_search_tsv_idx` GIN | column/index exist, but Phase 3 never populates it |
| 4 source lexical | `source_chunks.search_tsv`, `source_chunks_search_tsv_idx` GIN | column/index exist, but Phase 3 intentionally leaves it null |
| 5 graph | `wiki_links`, `wiki_links_from_idx`, `wiki_links_to_idx` | graph exists; no bounded traversal RPC yet |

`apps/worker/src/worker/handlers/parse.py` explicitly leaves `source_chunks.search_tsv` and `tsv_tokenizer_version` empty. `wiki.compile` likewise does not create `wiki_pages.search_tsv`. This is intentional Phase 4 debt, not a data bug. A Phase 4 indexing/backfill path is mandatory before lexical recall is benchmarked.

### Security and transport contract

The settled transport is PostgREST RPC with the requester's JWT. `apps/api/src/api/db/user.py::UserDb.rpc()` is the adapter. Search functions must remain `SECURITY INVOKER`, `STABLE`, RLS-filtered, and executable only by `authenticated`; user requests must never route through `worker.db.service` or service role.

`public.search_chunks(uuid, extensions.vector, int)` in migration `0008_embedding_dimension.sql` is the reference contract for vector RPCs:

- 1024-dimensional vector input, matching bge-m3/OpenRouter output;
- `set search_path = public` and schema-qualified `operator(extensions.<=>)`;
- all three required HNSW GUCs: `iterative_scan`, `ef_search`, `max_scan_tuples`;
- `strict_order` currently pinned at function definition;
- workspace filter and RLS both applied;
- service-role execution explicitly revoked in migration `0009_pipeline_ops.sql`.

Do not move RRF weights, candidate limits, graph depth, or `k` into SQL. SQL owns safe indexed retrieval; Python owns the reversible retrieval policy and fusion.

### Existing reusable code and conventions

- `packages/core/src/nexuswiki_core/tokenizer.py`: canonical `normalize()` then `bigram()` contract. Query and index paths must call these in that order; `bigram()` deliberately rejects unnormalized input.
- `apps/worker/src/worker/embedding.py`: OpenRouter embedding request, 1024-dimension validation, provider pinning, and `embedding_version()` format.
- `apps/api/src/api/main.py`: router registration; an eventual retrieval router belongs here, but an answer/SSE API remains Phase 5 scope.
- `apps/api/tests/conftest.py`: local Supabase fixture creates distinct authenticated tenant actors and is the correct base for real-RLS retrieval integration tests.
- `supabase/tests/0008_search_contract.sql`, `scripts/verify_search_contract.sh`, `scripts/ci_check_search_contract.sh`: established layered pattern: transactional catalog/behavioral SQL test + local runner + source-level CI guard.
- `supabase/spike/README.md` and `scripts/spike_db_transport.py`: prior HNSW corpus and plan-observation pattern. Small fixtures cannot prove an HNSW plan; use a sufficiently selective corpus or explicit controlled planner condition.

## Recommended Architecture

### Evidence identity and result shape

Make a single typed, internal `EvidenceHit` model shared by every channel. It needs a collision-proof identity and enough provenance for Phase 5, for example:

- `kind`: `wiki` or `source`;
- `evidence_id`: `wiki_pages.id` for lexical wiki hits, `wiki_embeddings.id` or canonical `wiki_id` for vector hits; `source_chunks.id` for source hits;
- `document_id`: canonical `wiki_id` / `raw_source_id`;
- title/slug or chunk index/content excerpt as retrieval metadata;
- `channels: set[str]` accumulated across channel results, never inferred from final position;
- optional raw rank and graph hop details for diagnostics.

Choose and document one canonical dedupe key **before RRF**. Recommended: dedupe wiki-vector chunks to the containing `wiki_id` for final evidence presentation, but retain the selected embedding chunk ID/excerpt in metadata. Source hits naturally dedupe by `source_chunks.id`. This avoids one long wiki page monopolising RRF with adjacent embedding chunks while preserving Phase 5 citation assembly.

Do not prematurely attempt Phase 5's anchor issuance, answer generation, citation intersection, or SSE event surface. Phase 4 returns a retrieval DTO/internal service result with stable evidence IDs and `meta`; Phase 5 consumes it.

### First wave: concurrent and degradable

Implement four independently callable channel adapters and schedule them with `asyncio.gather(..., return_exceptions=True)` (or named tasks with equivalent isolation):

1. wiki vector — query vector + `search_wiki_embeddings` RPC;
2. source vector — query vector + existing `search_chunks` RPC;
3. wiki lexical — `search_wiki_lexical` RPC, passing the Python-produced normalized bigram query and tokenizer version;
4. source lexical — `search_source_lexical` RPC with the same token contract.

Use the shared query vector once for both vector adapters, not two embedding-provider calls. Embedding failure is a shared vector dependency: record both dense channels as failed/unavailable, still run lexical retrieval, and return a successful degraded retrieval response when lexical channels work.

For each channel, capture elapsed time, requested candidate limit, returned count, error class/reason safe for callers, and hit identities. Never let a single channel exception cancel siblings. Treat a malformed RPC payload as a channel failure as well. Preserve `CancelledError`/request cancellation rather than converting it to a degraded result.

RRF should use only each channel's rank and the immutable policy weights. Correct score accumulation is `weight / (rrf_k + rank)` (define rank as 1-based and test it); no database similarity score may leak into RRF. Combine duplicate canonical evidence contributions across channels, retain per-channel attribution, deterministically tie-break by canonical ID, and stamp `policy_version` on every result and benchmark.

### Second wave: bounded graph expansion and re-fusion

Run graph only after first-wave RRF creates ordered seed wiki IDs. Default it off with a versioned feature flag in the Python policy; a default-off channel should appear in meta as `disabled`, not `failed`.

The graph SQL RPC should accept only seed IDs and a bounded request, never an unrestricted user graph query. It must:

- constrain `workspace_id` in every recursive term and rely on `SECURITY INVOKER` RLS;
- use only resolved links (`to_wiki_id is not null` / `resolved`);
- enforce `depth <= 2` and a policy-supplied, hard-SQL-capped fan-out per frontier node;
- carry a UUID path array and reject a node already in the path (cycle guard);
- cap total emitted candidates and return nearest-hop ordering/metadata;
- return wiki evidence in the same canonical result representation.

The graph channel has no query similarity. Its input rank must be derived deterministically from fused seed rank plus hop order (and recorded in documentation/tests), then it is added as channel 5 to the accumulated first-wave contributions and RRF is calculated again. Do not replace first-wave results with graph results.

### Query-embedding boundary — required decision checkpoint

`ApiSettings` is structurally forbidden from holding `OPENROUTER_API_KEY`; `worker.embedding.embed_texts()` requires `WorkerSettings`. Therefore a retrieval HTTP route cannot directly call OpenRouter under current design.

Recommended design: add a **private, worker-owned query embedding endpoint/service** alongside the resident worker, reachable only over Railway private networking. It accepts bounded text from the API, calls the existing embedding adapter with `WorkerSettings`, returns only the validated vector, and has no service-role database reads/writes. The API gets only an internal base URL operational setting; it never gets provider credentials. Run the queue loop and private endpoint under a single worker-process supervisor with graceful shutdown for both. Local test wiring injects an embedding client/fake instead of needing credentials.

This must be planned as a `checkpoint:decision` before implementation because it changes worker process topology and Railway configuration. Alternatives (a JWT-verifying Supabase Edge Function or another internal credential broker) are acceptable only if they preserve all of: no OpenRouter key in API/browser, requester isolation, explicit request-size/timeout/rate/cost bounds, and testability. Direct browser embedding and adding the key to `ApiSettings` are rejected.

## Database Work Needed

Plan one new migration (next numeric migration after existing `0010_budget_error_sqlstate.sql`; likely `0011_retrieval.sql`) rather than editing applied migrations.

It should contain:

1. A safe way for the worker to materialize `search_tsv` from Python-produced bigram text and set `tsv_tokenizer_version` atomically for source chunks and wiki pages. Prefer narrow RPC(s) that call `to_tsvector('simple', p_bigrams)` inside SQL and assert the owning workspace/source/page; do not send a tsvector textual encoding through PostgREST. Make initial backfill idempotent and make Phase 3 write paths invoke the same indexing operation for new/reprocessed content, otherwise lexical coverage regresses after the backfill.
2. Three retrieval RPCs: wiki-vector, wiki-lexical, source-lexical. Preserve the source-vector function's security/ACL/GUC characteristics. Vector RPCs should both declare all three HNSW GUCs; lexical RPCs should call `phraseto_tsquery('simple', p_bigrams)` and filter on the recorded tokenizer version so incompatible indexes are not silently mixed.
3. A bounded graph-expansion RPC as described above.
4. Explicit revoke/grant statements for every new RPC; no default public/anon/service-role execute privilege may survive.
5. `notify pgrst, 'reload schema'` after new/replaced RPCs.

Avoid an SQL function that exposes tunable weight, RRF k, requested final k, or unrestricted graph traversal. Limits sent to SQL should be constrained by the Python policy and additionally capped in SQL as a denial-of-service backstop.

## Policy, Benchmark, and Corpus Design

### Versioned policy layer

Create a pure module under `packages/core/src/nexuswiki_core/` (recommended `retrieval_policy.py` and `rrf.py`) for immutable policy constants, result types, RRF, and graph eligibility. Keep I/O orchestration in an API retrieval service (recommended `apps/api/src/api/services/retrieval.py` or package `api/retrieval/`).

Policy must record:

- a human-readable immutable `POLICY_VERSION` (bump for any semantic default/tuning change);
- RRF k; equal initial weights for channels 1–4; graph weight separately;
- per-channel over-fetch limits, final `requested_k`, vector/lexical SQL safety maxima, graph seeds, depth/fan-out/total cap;
- feature flag defaulting graph off;
- HNSW order mode/config identity used by the DB functions.

Every retrieval response, benchmark row, and policy-change record must include the policy version, corpus version/hash, timestamp, and git SHA where available. A policy change is not adopted until a before/after run against the same version-pinned corpus and golden set records recall and ranking metrics.

### Golden set

Store a reviewable, versioned fixture (recommended `packages/core/tests/fixtures/retrieval/golden_queries.v1.json` plus a provenance README) with 30–50 real-scenario Korean, English, and mixed-language queries. Do not create synthetic labels that merely mirror the query text.

Each query record should include: stable ID, language category, query, workspace/corpus fixture version, `requested_k`, required source chunk IDs, required wiki page IDs, explicitly allowed alternatives, and the maximum permitted rank for each required evidence unit. The pass predicate is the Phase 4 decision: all required evidence appears within top-k and at/better than its recorded threshold, with alternatives accepted explicitly.

Use a small seeded representative corpus with stable IDs/provenance. It must include cross-language terms, Korean NFC/NFD/full-width variants, dense-only and lexical-only cases, a graph-helpful relation, a graph-distractor/cycle, and enough rows/selectivity for honest HNSW plan assertions. Keep it separate from production data and make the benchmark runner fail if corpus/golden/policy versions do not match expected hashes.

Recommended recorded metrics:

- evidence recall@k: required evidence recovered / required evidence;
- strict query pass rate: queries meeting every label/rank threshold;
- MRR of the first required evidence and/or mean rank of required evidence;
- per-channel hit/contribution rate and p50/p95 channel + total latency;
- underfill count/rate by channel, particularly dense returned `<` requested candidate limit;
- graph-on versus graph-off delta by query and aggregate.

The benchmark needs to compare `strict_order` and `relaxed_order` on the same corpus, query set, policy, provider/model/version, repeat count and hardware/database context. Record quality and latency, choose the default based on evidence, then ensure the vector RPC contract and policy reflect the decision. Do not declare `relaxed_order` faster based only on an empty/small corpus.

## Observability Contract

Retrieval results need a non-answer `meta` now so Phase 5 can forward it in its first SSE `meta` event. At minimum include:

```json
{
  "policy_version": "...",
  "corpus_version": "...",
  "requested_k": 8,
  "returned_k": 6,
  "underfilled": true,
  "channels": {
    "wiki_vector": {"status": "ok", "requested_limit": 24, "returned": 18, "contribution": 3, "elapsed_ms": 31},
    "source_vector": {"status": "failed", "error_code": "provider_unavailable"},
    "wiki_lexical": {"status": "ok", "requested_limit": 24, "returned": 24, "contribution": 2, "elapsed_ms": 7},
    "source_lexical": {"status": "ok", "requested_limit": 24, "returned": 12, "contribution": 1, "elapsed_ms": 9},
    "graph": {"status": "disabled"}
  },
  "channel_hits": {"wiki_vector": 3, "wiki_lexical": 2, "source_lexical": 1}
}
```

Use safe, stable error codes; do not include raw provider/PostgREST error bodies, credentials, or cross-tenant identifiers. Define `underfilled` both at final result and per channel. The key dense signal is `returned < requested_limit`, because HNSW post-filtering may short-return without an error even with `strict_order` enabled.

## Validation Architecture

The phase can produce a strong `04-VALIDATION.md` if the plans include the following proof surfaces.

| Requirement | Automated proof | Live/manual evidence |
|---|---|---|
| RTV-01 | pure orchestration tests assert all four first-wave adapters start concurrently; graph receives only fused seed order; final result is re-fused | benchmark artifact with graph off/on comparison |
| RTV-02 | unit tests prove rank-only RRF, equal initial weights, deterministic dedupe/tie-break, and policy version propagation | before/after policy benchmark record |
| RTV-03 | SQL catalog tests assert both vector RPCs have all three GUCs; behavioral RPC checks | source guard extended for every current vector function |
| RTV-04 | benchmark runner executes both orders against same pinned inputs and rejects missing comparison metadata | `docs/ops/hnsw-order-benchmark.md` records selected default/rationale |
| RTV-05 | tests assert `channel_hits`, per-channel limit/return, contribution, failures and final underfill | benchmark emits channel underfill/contribution tables |
| RTV-06 | schema-validation test requires 30–50 valid labelled queries and allowed alternatives/provenance | reviewed corpus manifest and benchmark output stored in docs/artifact |
| RTV-07 | SQL/integration tests prove depth 2, fan-out/total cap, cycle guard, unresolved-link exclusion, default-off flag | graph-on delta report proves whether flag may change |
| RTV-08 | transactional real-DB test uses `EXPLAIN (FORMAT JSON)` and recursively inspects plan JSON for `Index Scan` using each HNSW index; negative/source guards catch dropped GUC/index names | local runner output is retained; meaningful corpus cardinality is documented |
| RTV-09 | one adapter/RPC/provider is forced to fail; siblings still fuse and meta reports only the failed channel; all failures have explicit degraded result | structured retrieval logs/benchmark record show failure schema |

Recommended test/file layout:

- `packages/core/tests/test_rrf.py`, `test_retrieval_policy.py`, and golden-set schema/metric tests: no Docker or secrets.
- `apps/api/tests/test_retrieval_service.py`: concurrent-wave, failure isolation, response-meta, feature-flag and query-embedder fake tests.
- `apps/api/tests/test_retrieval_router.py`: requester-JWT route wiring/error rendering, only if Phase 4 introduces the retrieval endpoint.
- `apps/api/tests/test_hybrid_search_integration.py`: marked/skipped without local Supabase, reusing current two-tenant fixture; validates each RPC, RLS isolation, lexical indexing and graph bounds.
- `supabase/tests/0011_retrieval_contract.sql` + `scripts/verify_retrieval_contract.sh`: RPC function properties, ACLs, GUCs, `EXPLAIN` plan JSON and transactional fixture cleanup.
- Extend `scripts/ci_check_search_contract.sh` or add a focused retrieval source guard so future migrations cannot silently remove required vector function properties. CI cannot run the Docker/Supabase plan test, so retain both layers.
- `scripts/benchmark_retrieval.py`, fixture corpus/golden files, and `docs/ops/hnsw-order-benchmark.md` / `docs/ops/retrieval-policy-benchmark.md`.

The test suite must avoid asserting an HNSW scan over the tiny 30-row `0008_search_contract.sql` fixture: that small data set correctly encourages a non-HNSW plan. Reuse/adapt the prior 50,000-row/selective corpus approach, or a documented smaller corpus that empirically selects the HNSW indexes, and assert the actual plan node/index names rather than text formatting alone.

## Constraints and Pitfalls

1. **Lexical indexes are currently empty.** Benchmarking before backfill/write-path indexing creates a misleading “vector wins” result.
2. **No credential leakage to API.** `ApiSettings` is intentionally tested for absence of `OPENROUTER_API_KEY`; preserve this while solving query embedding.
3. **PostgREST `max_rows`.** Keep per-channel candidates intentionally bounded below the platform cap and treat a truncated response as observable, not as exhaustive recall.
4. **HNSW post-filter underfill.** The three GUCs are a package; `strict_order` alone does not raise `ef_search` or scanning budget. Log the shortfall instead of silently padding with unrelated evidence.
5. **Functions are recreated by migration.** Any replacement must restore `SECURITY INVOKER`, `STABLE`, `search_path`, GUCs, ACLs, and PostgREST schema reload. Dropping/recreating a function loses grants.
6. **Do not conflate RLS and workspace parameter.** The RPC parameter bounds the query, but requester JWT/RLS is the authority. Integration tests must prove a foreign workspace ID does not reveal rows.
7. **Graph recursion must stay bounded in SQL.** A Python-only cap after an unbounded recursive CTE is too late to protect database work.
8. **Partial failure semantics.** A disabled channel is not a failed channel; an absent query embedding should mark both dense channels unavailable but preserve lexical success.
9. **Policy auditability.** If `POLICY_VERSION` is not in benchmark and response metadata, later improvements cannot be attributed or rolled back.
10. **Scope fence.** Phase 4 stops at evidence retrieval and retrieval meta. Citation anchor issuance/parsing, answer creation, SSE, user-facing dashboard and graph canvas APIs belong to later phases.

## Requirement Coverage Map

| Requirement | Planned capability |
|---|---|
| RTV-01 | four concurrent first-wave adapters → RRF → fused wiki seeds → bounded channel-5 RPC → re-fusion |
| RTV-02 | immutable Python policy + pure rank-only RRF; SQL limited to retrieval/index work |
| RTV-03 | vector RPC definitions for both dense channels retain/test `iterative_scan`, `ef_search`, `max_scan_tuples` |
| RTV-04 | same-input strict-vs-relaxed benchmark and decision document |
| RTV-05 | response meta and benchmark records expose channel hits, contribution, requested/returned limits and underfill |
| RTV-06 | version-pinned representative corpus plus 30–50 Korean/English/mixed evidence-labelled golden queries |
| RTV-07 | default-off policy flag plus SQL-recursive depth/fan-out/total/cycle bounds, graph-on value measurement |
| RTV-08 | real-DB JSON EXPLAIN regression test asserting named HNSW index scans |
| RTV-09 | `return_exceptions`/per-channel result envelopes; degraded success with explicit safe failure meta |

## Suggested Plan Decomposition

1. **Tracer / decision gate:** settle worker-owned query embedding boundary; introduce typed policy/result/RRF foundation and one source-vector + lexical path from API adapter to evidence meta. Verify no API secret capability, ordinary unit tests, and local integration/RLS proof.
2. **Search database completion:** migration for indexing/backfill and all retrieval/graph RPC contracts; transactional SQL tests, ACL/GUC guards, real lexical hits and HNSW EXPLAIN coverage.
3. **Five-channel orchestrator:** four-channel concurrency, exception isolation, RRF, bounded default-off graph second wave/re-fusion, feature/meta observability tests.
4. **Measurement gate:** golden corpus/query suite, benchmark runner, strict-vs-relaxed decision, equal-weight baseline, graph-off/on evidence and recorded policy-change protocol.

The benchmark/golden-set task can begin in parallel with database completion, but it must finish before final policy tuning or enabling graph by default. The query-embedding topology is the first dependency because it determines the tracer endpoint's executable vector path.

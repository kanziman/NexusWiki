---
phase: 04-hybrid-retrieval-and-fusion
verified: 2026-08-11T10:00:00Z
status: gaps_found
score: 6/10 must-haves verified
behavior_unverified: 0
overrides_applied: 0
gaps:
  - truth: "A bounded private worker query-embedding boundary remains available for normal retrieval traffic."
    status: failed
    reason: "The private listener consumes a process-lifetime request counter and never refills it. At the configured default, request 101 and every request after it return 429 until the worker restarts; the API then silently degrades all dense channels to lexical-only."
    artifacts:
      - path: apps/worker/src/worker/query_embedding.py
        issue: "_remaining_requests is initialized once, decremented for every authenticated call, and has no time-window/token-bucket refill or recovery path."
    missing:
      - "Replace the lifetime counter with a time-based refill/token-bucket (or an explicit concurrency-only control), define quota accounting for failed and timed-out calls, and test restored capacity."
  - truth: "The pinned golden corpus records an evidence-backed strict_order versus relaxed_order choice."
    status: failed
    reason: "No comparable strict/relaxed run or raw run reference exists. The decision record explicitly says that neither comparison was executed and the benchmark emits order_mode=not_measured_fixture_adapter."
    artifacts:
      - path: docs/ops/hnsw-order-benchmark.md
        issue: "Records the absence of measurement instead of the Plan 04 Task 3 required comparison."
      - path: scripts/benchmark_retrieval.py
        issue: "The --verify fixture adapter does not execute database/HNSW order-mode comparisons."
    missing:
      - "Run and retain same-input strict_order and relaxed_order benchmark records with raw run references, or formally re-scope the roadmap requirement."
  - truth: "EXPLAIN regression tests assert HNSW Index Scan use for both source and wiki vector retrieval."
    status: failed
    reason: "The SQL contract checks that the three HNSW GUCs are configured, but contains no EXPLAIN assertion for source_chunks_embedding_idx or wiki_embeddings_embedding_idx."
    artifacts:
      - path: supabase/tests/0011_retrieval_contract.sql
        issue: "No EXPLAIN/JSON-plan assertion names either required HNSW index."
    missing:
      - "Seed a selective representative corpus and add an executable EXPLAIN regression assertion naming both HNSW indexes."
  - truth: "Graph-off and graph-on results are recorded on the pinned golden set before graph value is assessed."
    status: failed
    reason: "The graph remains safely disabled, but no off/on comparison was run; the runner has no graph toggle and reports graph_delta.status=not_measured_fixture_adapter."
    artifacts:
      - path: docs/ops/hnsw-order-benchmark.md
        issue: "Explicitly records that graph off/on was not measured."
      - path: scripts/benchmark_retrieval.py
        issue: "Has no graph off/on execution mode."
    missing:
      - "Add graph toggling and per-query/aggregate graph delta recording, then retain paired golden-set runs before any graph promotion decision."
deferred:
  - truth: "Comparable strict/relaxed and graph off/on operational measurements"
    addressed_in: "Phase 7"
    evidence: "04-04-SUMMARY.md, WINDOWS #10, and the benchmark decision record explicitly defer production-like measurements to Phase 7 OPS. This does not remove the Phase 4 roadmap/plan gaps."
---

# Phase 4: Hybrid Retrieval and Fusion Verification Report

**Phase Goal:** 질문 하나가 5채널을 거쳐 **측정 가능하게** 옳은 근거 집합을 돌려준다

**Verified:** 2026-08-11T10:00:00Z

**Status:** gaps_found

**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
| --- | --- | --- | --- |
| 1 | Pinned multilingual golden set informs recorded order-mode tuning decisions. | ✗ FAILED | 36-query fixture exists, but strict/relaxed was not measured or recorded. |
| 2 | Four concurrent channels are RRF-fused before bounded optional graph re-fusion. | ✓ VERIFIED | `RetrievalService.retrieve()` gathers four RPC adapters; graph uses fused wiki seeds only. Barrier and graph tests pass. |
| 3 | A failed channel leaves a useful response and reports safe channel metadata. | ✓ VERIFIED | Per-channel exception envelopes and cancellation re-raise are implemented and covered by focused tests. |
| 4 | Returned/underfill and channel contribution are first-class metadata. | ✓ VERIFIED | Retrieval response meta exposes requested, returned, underfill, channel status, raw IDs, contribution, and policy version. |
| 5 | HNSW planner regression is detected by EXPLAIN. | ✗ FAILED | No executable EXPLAIN assertion names `source_chunks_embedding_idx` or `wiki_embeddings_embedding_idx`. |
| 6 | RRF is rank-only with immutable/versioned Python policy and deterministic canonical ties. | ✓ VERIFIED | `retrieval_policy.py` and `rrf.py`; policy/RRF tests pass. |
| 7 | API/browser lack provider credentials and the worker embedding boundary is safely bounded. | ✗ FAILED | Secret boundary is present, but `QueryEmbeddingService` permanently exhausts `max_requests` without refill. |
| 8 | Versioned bigrams and user/service RPC boundaries are substantive and wired. | ✓ VERIFIED | `0011_retrieval.sql`, worker lexical calls, RLS integration test, and CI contract gate pass. |
| 9 | Graph SQL is bounded, cycle-safe, workspace-scoped, and default-off. | ✓ VERIFIED | `expand_wiki_graph` bounds seeds/fanout/total/depth and policy defaults to disabled. |
| 10 | Graph value is measured off/on before it is assessed for promotion. | ✗ FAILED | The record and runner explicitly state no graph comparison was run. |

**Score:** 6/10 must-haves verified (0 present, behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
| --- | --- | --- | --- |
| `packages/core/src/nexuswiki_core/retrieval_policy.py` | Immutable versioned policy | ✓ VERIFIED | Frozen dataclass and immutable mappings; tests pass. |
| `packages/core/src/nexuswiki_core/rrf.py` | Rank-only deterministic RRF | ✓ VERIFIED | Canonical IDs, dedupe, contributions, and tie ordering are tested. |
| `apps/api/src/api/services/retrieval.py` | Four-channel/two-wave orchestration | ✓ VERIFIED | Requester-JWT RPC flow is live; failures are isolated. |
| `apps/worker/src/worker/query_embedding.py` | Bounded private vector service | ✗ FAILED | Lifetime quota makes normal dense retrieval non-durable. |
| `supabase/migrations/0011_retrieval.sql` | Retrieval RPC and graph boundary | ✓ VERIFIED | ACL/GUC/graph bounds are substantive; static gate passes. |
| `supabase/tests/0011_retrieval_contract.sql` | HNSW EXPLAIN regression contract | ✗ FAILED | Does not test query plans or named HNSW indexes. |
| `scripts/benchmark_retrieval.py` | Reproducible operational comparisons | ✗ FAILED | Fixture contract verification is reproducible, not strict/relaxed or graph off/on measurement. |

### Key Link Verification

| From | To | Via | Status | Details |
| --- | --- | --- | --- | --- |
| Retrieval service | `UserDb.rpc` | requester-JWT search RPCs | ✓ WIRED | Four adapters invoke authenticated RPC names; no worker service DB import in API retrieval code. |
| Retrieval service | Private worker embedder | `QueryEmbeddingClient` | ⚠️ PARTIAL | Injection and credential boundary are wired, but the listener's non-refilling quota breaks sustained operation. |
| Parse/compile handlers | lexical writer RPCs | normalized bigrams | ✓ WIRED | Handler/service paths and tests exercise the writer methods. |
| First-wave RRF | `expand_wiki_graph` | fused wiki seed IDs | ✓ WIRED | Graph only runs after first fusion, with capped seed/fanout/total parameters. |
| SQL contracts | planner behavior | EXPLAIN named-index assertion | ✗ NOT WIRED | No EXPLAIN test exists. |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| --- | --- | --- | --- |
| Focused retrieval, boundary, policy, RRF, integration, and golden tests | `UV_CACHE_DIR=/tmp/nexuswiki-uv-cache uv run pytest -q ...` | 27 passed | ✓ PASS |
| Pinned fixture benchmark contract | `UV_CACHE_DIR=/tmp/nexuswiki-uv-cache uv run python scripts/benchmark_retrieval.py --verify` | exit 0; explicitly `not_measured_fixture_adapter` | ✓ PASS (fixture contract only) |
| Secret and SQL static contracts | `bash scripts/ci_check_query_embedding_boundary.sh && bash scripts/ci_check_retrieval_contract.sh` | exit 0 | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Status | Evidence |
| --- | --- | --- | --- |
| RTV-01 | 04-03 | ✓ SATISFIED | Four concurrent first-wave adapters, RRF, fused-seed graph re-fusion and tests. |
| RTV-02 | 04-01 | ✓ SATISFIED | Rank-only RRF and immutable Python policy. |
| RTV-03 | 04-02 | ✓ SATISFIED | Both vector RPCs set all three required HNSW GUCs. |
| RTV-04 | 04-04 | ✗ BLOCKED | Strict/relaxed comparison and selection evidence do not exist. |
| RTV-05 | 04-01/03 | ✓ SATISFIED | Channel contribution and underfill metadata are returned. |
| RTV-06 | 04-04 | ✓ SATISFIED | Pinned 36-query Korean/English/mixed golden set validates. |
| RTV-07 | 04-02/03/04 | ⚠️ PARTIAL | SQL and default-off safety are satisfied; promised golden-set off/on value comparison is absent. |
| RTV-08 | 04-02 | ✗ BLOCKED | No named-index EXPLAIN regression assertion. |
| RTV-09 | 04-01/03 | ✓ SATISFIED | Isolated channel failures yield safe meta and remaining evidence; cancellation propagates. |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| --- | --- | --- | --- |
| `apps/worker/src/worker/query_embedding.py` | 50–65 | Non-refilling lifetime request quota | 🛑 BLOCKER | Dense retrieval becomes permanently unavailable after ordinary traffic. |

### Gaps Summary

The phase has a substantive retrieval implementation and focused tests, but its goal is not achieved. Dense retrieval has a permanent capacity-exhaustion defect, the required HNSW EXPLAIN regression is absent, and the planned order-mode and graph value comparisons were deliberately not run. The Phase 7 deferral is documented, but cannot turn Phase 4's unfulfilled roadmap/plan contracts into a pass.

---

_Verified: 2026-08-11T10:00:00Z_
_Verifier: the agent (gsd-verifier)_

---
phase: 07-integration-and-ops-baseline
verified: 2026-08-13T12:28:00+09:00
status: passed
score: 5/5 must-haves verified
behavior_unverified: 0
overrides_applied: 0
gaps: []
browser_verification:
  - test: "Owner Operations tab at a 360×800 viewport."
    result: "Passed: refresh control remained within viewport; document had no horizontal overflow; pipeline container measured 560px scroll width in 310px client width with overflow-x:auto."
  - test: "Long pipeline stage label on the rendered row element."
    result: "Passed: rendered element had overflow:hidden, text-overflow:ellipsis, white-space:nowrap, scrollWidth 716px > clientWidth 298px, and matching title text."
---

# Phase 7: Integration and Ops Baseline Verification Report

**Phase Goal:** 조각들이 실제로 함께 동작함이 증명되고, 품질·비용·격리에 이후 회귀를 판정할 기준선이 생긴다
**Verified:** 2026-08-13T12:28:00+09:00
**Status:** passed
**Re-verification:** Yes — F-01 write-isolation and F-02 planning-state remediation

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
| --- | --- | --- | --- |
| 1 | Empty-workspace ingest → compile → embed → retrieval passes. | ✓ VERIFIED | `test_ingest_pipeline_reaches_retrieval` creates text/file/URL sources via API, drains real claim/complete queue transitions through parse/compile/link/embed handlers, and calls the retrieval API. Only URL, LLM, and embedding transports are deterministic doubles. Focused test passed in the fresh Phase-7 backend run. |
| 2 | Duplicate content does not grow rows and shrinking reprocessing removes residual rows. | ✓ VERIFIED | `test_duplicate_normalized_text_does_not_grow_rows` asserts API 409 and unchanged raw-source/chunk/page/embedding counts. `test_shorter_reprocess_removes_stale_chunks_and_embeddings` requires multiple original chunks, a lower post-reprocess count, contiguous indices, and no remaining embedding index beyond the new chunk count. |
| 3 | Cross-tenant attempts across application paths (read/write/jobs/Storage) are blocked by a suite. | ✓ VERIFIED | Commit `a1d1143` adds a declarative nine-table requester-JWT UPDATE/DELETE matrix with own controls plus A→B, B→A, non-member, and anonymous denials; it explicitly records derived non-writable boundaries and tests supported source INSERT API controls/denials. The focused local-Supabase rerun exited successfully. Existing read, queue-RPC, and Storage checks remain in the suite. |
| 4 | Golden quality and channel latency baseline is recorded for regression decisions. | ✓ VERIFIED | Both immutable `phase-07-{strict,relaxed}-order.json` records pin the same clean SHA `135a0f16…`, repeat count 3, corpus/golden/policy manifests, full-path metrics, per-channel p50/p95, and two raw scoped EXPLAIN captures. Fresh comparator: `{"status":"ok","quality_delta":-0.2222222222222222}`. Raw plans name `source_chunks_embedding_idx` and `wiki_embeddings_embedding_idx`; both records truthfully record `representative_hnsw_observed`. No retrieval-policy file changed in the evidence capture range. |
| 5 | Workspace costs and pipeline health are observable without leaking operational internals. | ✓ VERIFIED | `GET /workspaces/{id}/operations` enforces requester-JWT `has_workspace_role(..., min_role=editor)`, returns a fixed allowlist budget/pipeline/observed-at DTO, and `OperationsPanel` is rendered only from the existing Settings route for owner/editor. API tests prove owner/editor 200, unauthenticated 401, viewer/foreign/non-member 403, stage order, and sensitive-key absence; dashboard tests prove viewers make no request and refresh retains the last snapshot. |

**Score:** 5/5 truths verified.

### Decision Coverage (D-01 through D-12)

| Decision | Status | Evidence |
| --- | --- | --- |
| D-01 | VERIFIED | Pipeline fixture doubles only URL/LLM/embedding clients; local Supabase, Storage, queue RPCs, and retrieval stay real. |
| D-02 | VERIFIED | E2E test asserts terminal jobs plus persisted source/page/chunk/embedding evidence and retrieval evidence. |
| D-03 | VERIFIED | Conventionally named pytest modules are collected; fresh focused Phase-7 backend run passed. |
| D-04 | VERIFIED | Shared fixture creates text/file/URL API sources and checks workspace-prefixed file Storage path. |
| D-05 | VERIFIED | Existing Settings route and 640px shell are retained; no top-level navigation added. |
| D-06 | VERIFIED | Server-side editor-or-owner operations endpoint, budget and five-stage snapshot tested. |
| D-07 | VERIFIED | One `useEffect` entry fetch plus manual refresh; no timer/polling code; disabled/`aria-busy` refresh and error retention tested. |
| D-08 | VERIFIED | Server authorization is authoritative and the fixed DTO/panel omit payload, errors, usage metadata, provider, and model fields. |
| D-09 | VERIFIED | Real-local role-complete principals cover all-nine-table reads and declarative supported mutation boundaries: own controls, A→B/B→A/non-member/anonymous denials, derived-table 42501 boundaries, source INSERT API, queue RPC, and Storage. |
| D-10 | VERIFIED | Canonical 25k source + 25k wiki-vector, 1024-dimension corpus is pinned in the record/runner contract. |
| D-11 | VERIFIED | Existing multilingual evidence-labelled golden fixture is pinned and measured through `RetrievalService.retrieve()`. |
| D-12 | VERIFIED | Strict/relaxed records share SHA/repeat/policy/data pins; comparator accepts them and document appends the interpretation without policy change. |

### Required Artifacts

| Artifact | Expected | Status | Details |
| --- | --- | --- | --- |
| `apps/api/tests/fixtures/pipeline.py` | Shared local-stack harness | ✓ VERIFIED | Substantive API/worker/queue/retrieval harness; consumed by all OPS-02/03/04 tests. |
| `apps/api/tests/test_pipeline_e2e.py` | OPS-02 tracer | ✓ VERIFIED | Runs the shared harness from an empty workspace. |
| `apps/api/tests/test_reingestion_idempotency.py` | OPS-03 proof | ✓ VERIFIED | Covers duplicate count invariance and actual shrinking cleanup. |
| `apps/api/tests/test_tenant_isolation_full_path.py` | OPS-04 matrix | ✓ VERIFIED | Requester-JWT read plus UPDATE/DELETE matrices cover all nine tables; supported INSERT API boundary, queue RPC, and Storage paths are also exercised. |
| `scripts/benchmark_retrieval.py` | Pinned full-path records/comparator | ✓ VERIFIED | Schema validates scoped EXPLAIN evidence and comparator pin compatibility. |
| `docs/ops/benchmark-records/phase-07-*.json` | Immutable local arms | ✓ VERIFIED | Distinct committed strict/relaxed records with complete captures and HNSW evidence. |
| `docs/ops/hnsw-order-benchmark.md` | Append-only interpretation | ✓ VERIFIED | New Phase 7 section records exact pins, quality/latency, HNSW decision, and policy non-change. |
| `apps/api/src/api/routers/jobs.py` | Safe snapshot endpoint | ✓ VERIFIED | Fixed server allowlist, RLS-scoped reads, and editor authorization. |
| `apps/dashboard/components/OperationsPanel.tsx` | Manual-refresh Operations UI | ✓ VERIFIED | Real `apiFetch` data flow, no polling/retry/cancel surface, safe error handling. |
| `apps/dashboard/tests/OperationsPanel.test.tsx` | UI contract | ✓ VERIFIED | Covers loading, populated/empty/partial, error retention, all-zero rows, roles/no viewer request, tabs, and keyboard use. |

### Key Link Verification

| From | To | Via | Status | Details |
| --- | --- | --- | --- | --- |
| Source API | Queue → worker stages → retrieval API | `PipelineHarness.create_three_sources`, `claim_job`, handler seams, `RetrievalService` route | ✓ WIRED | Exercised by the OPS-02 integration test. |
| Reprocess parse | `upsert_and_truncate` cleanup → chunks/embeddings | Real ServiceDb reprocess and postconditions | ✓ WIRED | Exercised by shrinking test. |
| Isolation matrix | Requester JWT → API/UserDb → local RLS | `authed_client`, `user_db`, local REST/Storage calls | ✓ WIRED | Real requester-JWT read/write controls and cross-tenant/non-member/anonymous denials traverse local RLS; non-writable derived boundaries assert 42501. |
| Corpus generator | `RetrievalService.retrieve` → record/comparator | benchmark runner with immutable pins | ✓ WIRED | Records and fresh comparator validate the connection. |
| Settings tab | OperationsPanel → `GET /operations` → server DTO | Role-gated tab and `apiFetch` | ✓ WIRED | Dashboard/API tests demonstrate role gate and snapshot flow. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| --- | --- | --- | --- | --- |
| `OperationsPanel.tsx` | `snapshot` | `apiFetch('/workspaces/{id}/operations')` | Endpoint aggregates RLS-scoped workspaces, usage events, and `type,status` jobs into a fixed DTO | ✓ FLOWING |
| Benchmark records | metrics/captures | Full-path retrieval runner and raw database EXPLAIN plans | Record contains real captured metrics and plan JSON, not a static fixture | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| --- | --- | --- | --- |
| F-01 isolation write matrix | `UV_CACHE_DIR=/tmp/nexuswiki-uv-cache uv run pytest -q apps/api/tests/test_tenant_isolation_full_path.py` | Fresh F-01 rerun completed after exercising the 32 collected isolation cases; the execution harness retained progress dots but not the pytest footer. | ✓ PASS |
| OPS focused pipeline/idempotency/isolation/operations contracts | `UV_CACHE_DIR=/tmp/nexuswiki-uv-cache uv run pytest -q apps/api/tests/test_pipeline_e2e.py apps/api/tests/test_reingestion_idempotency.py apps/api/tests/test_tenant_isolation_full_path.py apps/api/tests/test_jobs_router.py` | Fresh run completed; `--collect-only` independently confirms 51 selected tests (3 pipeline/idempotency, 32 isolation, 16 jobs). The execution harness retained progress dots but not the terminal footer. | ✓ PASS |
| Retrieval record schema | `UV_CACHE_DIR=/tmp/nexuswiki-uv-cache uv run pytest -q packages/core/tests/test_retrieval_golden.py` | 18 passed | ✓ PASS |
| Record comparator | `uv run python scripts/benchmark_retrieval.py compare-order-records ...` | `{"status":"ok","quality_delta":-0.2222222222222222}` | ✓ PASS |
| Dashboard operations/UI type safety | `pnpm --dir apps/dashboard test && pnpm --dir apps/dashboard typecheck` | 17 files / 82 tests passed; typecheck passed | ✓ PASS |
| Full Python suite | `UV_CACHE_DIR=/tmp/nexuswiki-uv-cache uv run pytest -rs` | 435 tests collected; command completed after reporting through 37% in captured output, but the terminal footer was not retained by the execution harness | ⚠️ INCONCLUSIVE CAPTURE |

### Requirements Coverage

| Requirement | Source Plan | Status | Evidence |
| --- | --- | --- | --- |
| OPS-02 | 07-01 | ✓ SATISFIED | Real-local ingest-to-retrieval tracer. |
| OPS-03 | 07-01 | ✓ SATISFIED | Duplicate and shrinking reprocess tests. |
| OPS-04 | 07-02 | ✓ SATISFIED | F-01 adds the all-nine-table requester-JWT UPDATE/DELETE matrix, supported INSERT API boundary, and explicit non-writable derived-table controls. |
| OPS-05 | 07-03 | ✓ SATISFIED | Pinned quality/latency/HNSW baseline and valid comparator. |
| OPS-06 | 07-04 | ✓ SATISFIED | Server-authorized safe snapshot plus Settings-only Operations panel. |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| --- | --- | --- | --- |
| `.planning/phases/07-integration-and-ops-baseline/07-PATTERNS.md` | 3–4 | Trailing whitespace | ℹ️ Info | Documentation-only formatting; no delivery impact. |

## Browser Layout Verification

`agent-browser` verified the owner Operations tab in a local authenticated session. At a 360×800 viewport, the refresh control stayed fully visible, the document had no horizontal overflow, and the stage table used its intended internal horizontal scroll container (560px scroll width / 310px client width, `overflow-x:auto`).

The production snapshot uses a fixed set of five server-owned labels, so a naturally long label cannot occur through the current API. To verify the actual browser CSS behavior, the check injected a long label into the already-rendered stage-row element and preserved its `title`. The element remained in view and measured `scrollWidth` 716px over `clientWidth` 298px with `overflow:hidden`, `text-overflow:ellipsis`, and `white-space:nowrap`; its complete `title` matched the label.

## Completion Summary

Phase 7 has executable evidence for E2E ingest, shrinking reprocessing, the full requester-JWT isolation boundary, HNSW-scale baseline records, and a safely authorized operations view. F-01 (`a1d1143`) closes the earlier write-isolation gap; F-02 synchronizes Phase 7 planning records with that evidence. The root Python-suite invocation still has an inconclusive captured footer (435 tests collected and output retained through 37%), so this report does not claim a newly captured full-suite total. The two browser-layout backstops are now verified with the scope and limitation recorded above.

_Verified: 2026-08-13T12:28:00+09:00_
_Verifier: the agent (gsd-verifier)_

---
phase: 04-hybrid-retrieval-and-fusion
reviewed: 2026-08-11T00:00:00Z
depth: standard
files_reviewed: 36
files_reviewed_list:
  - apps/api/src/api/main.py
  - apps/api/src/api/routers/retrieval.py
  - apps/api/src/api/services/__init__.py
  - apps/api/src/api/services/retrieval.py
  - apps/api/src/api/settings.py
  - apps/api/tests/test_hybrid_search_integration.py
  - apps/api/tests/test_retrieval_service.py
  - apps/worker/src/worker/__main__.py
  - apps/worker/src/worker/db/service.py
  - apps/worker/src/worker/handlers/compile.py
  - apps/worker/src/worker/handlers/parse.py
  - apps/worker/src/worker/query_embedding.py
  - apps/worker/src/worker/settings.py
  - apps/worker/tests/test_handlers.py
  - apps/worker/tests/test_query_embedding.py
  - apps/worker/tests/test_service_client.py
  - docs/architecture/query-embedding-boundary.md
  - docs/ops/hnsw-order-benchmark.md
  - docs/ops/migration-0011-record.md
  - docs/ops/retrieval-policy-change-log.md
  - packages/core/src/nexuswiki_core/retrieval_policy.py
  - packages/core/src/nexuswiki_core/rrf.py
  - packages/core/tests/fixtures/retrieval/README.md
  - packages/core/tests/fixtures/retrieval/golden_queries.v1.json
  - packages/core/tests/fixtures/retrieval/representative_corpus.v1.json
  - packages/core/tests/test_retrieval_golden.py
  - packages/core/tests/test_retrieval_policy.py
  - packages/core/tests/test_rrf.py
  - packages/core/tests/test_settings.py
  - railway.json
  - scripts/benchmark_retrieval.py
  - scripts/ci_check_query_embedding_boundary.sh
  - scripts/ci_check_retrieval_contract.sh
  - scripts/verify_retrieval_contract.sh
  - supabase/migrations/0011_retrieval.sql
  - supabase/tests/0011_retrieval_contract.sql
findings:
  critical: 0
  warning: 0
  info: 3
  total: 3
status: clean
---

# Phase 04: Code Review Report

**Reviewed:** 2026-08-11
**Depth:** standard
**Files Reviewed:** 36
**Status:** issues_found

## Summary

Reviewed the Phase 04 retrieval policy/fusion implementation, authenticated API-to-worker embedding boundary, database retrieval contracts, worker lexical indexing, fixture benchmark, tests, and associated operational documentation. The requester-JWT RPC boundary and failure envelopes are consistently applied, but the private embedding listener has a lifetime request counter that permanently disables dense retrieval after ordinary traffic volume.

## Narrative Findings (AI reviewer)

## Critical Issues

None open. (See CR-01 correction below.)

### CR-01 — CORRECTED 2026-08-11: already fixed, not an open issue

**Original claim:** `max_requests` initializes `_remaining_requests` once for the lifetime of the long-lived worker listener and is never replenished, so query embedding capacity is exhausted permanently after 100 requests.

**Correction:** This finding was stale against current `HEAD` when first written. `apps/worker/src/worker/query_embedding.py` (current, lines ~30-79) uses a lock-protected monotonic token bucket (`_tokens`, `_last_refill`, `_reserve_token()`), not a lifetime counter — fixed in commit `6a14144` ("feat(04-05): add refilling embedding quota"), which predates this review. `docs/architecture/query-embedding-boundary.md` documents the token-bucket design as the approved implementation. Verified independently during Phase 04→05 transition (2026-08-11):
- `git log -- apps/worker/src/worker/query_embedding.py` shows `6a14144` replacing `_remaining_requests` with `_tokens`/refill logic.
- `apps/worker/tests/test_query_embedding.py::test_token_bucket_refills_after_exhaustion_without_restart` and `::test_exhausted_bucket_admits_only_one_parallel_contender_after_refill` both exist and pass (9/9 in the file, `pytest -q`).

Frontmatter `critical`/`status` corrected from 1/`issues_found` to 0/`clean` to reflect this.

---

## Plan 04-09 Review (scoped)

**files_reviewed:** 3

- `scripts/benchmark_retrieval.py`
- `packages/core/tests/test_retrieval_golden.py`
- `docs/ops/hnsw-order-benchmark.md`

**Diff scope confirmed via** `git diff 048d46ca47a7c87542af208940b10fe1287f6f91^..e0f3837`: `_pins()` gained a `git_sha` key (8→9 pinned fields); `compare_order_records()` gained a `{left.order_mode, right.order_mode} == {strict_order, relaxed_order}` assertion; 3 new pytest regression tests; doc updated to mark v4 strict/relaxed superseded-invalid and record the new v5 pair.

### Findings

**Critical:** none.

**Warning:** none.

**Info:**

1. `scripts/benchmark_retrieval.py:200` (new `order_pair_mode_invalid` line) follows the file's existing dense one-statement-per-line style — pre-existing project convention, not a regression introduced by 04-09.
2. The order_mode check is short-circuited by the `or` in the preceding `_pins`/policy comparison (`scripts/benchmark_retrieval.py:200`), so it only executes when pins already match — correctly exercised by `test_compare_order_records_rejects_matching_order_mode_pair`, which deliberately uses pin-identical records to isolate the new assertion. No gap found.

### Verification performed

- Recomputed `_pins()` field count (9) matches the doc's claim.
- Loaded all six referenced JSON fixtures (v4-strict, v4-relaxed, v4-graph-off, v4-graph-on, v5-strict, v5-relaxed) and confirmed `git_sha`/`order_mode` values match what the tests assert and the markdown table claims.
- Ran `pytest packages/core/tests/test_retrieval_golden.py -v`: 13/13 passed, including all 3 new regression tests.
- Confirmed `compare_graph_records` (unchanged logic, shares `_pins()`) still accepts the valid v4 graph pair — no regression from the shared helper change.

**Scoped status: clean** (the pre-existing CR-01 finding above, from `apps/worker/src/worker/query_embedding.py`, is out of scope for plan 04-09 and remains open.)

---

_Reviewed: 2026-08-11T00:00:00Z_
_Reviewer: the agent (gsd-code-reviewer)_
_Depth: standard_

_Plan 04-09 scoped re-review appended: 2026-08-11_
_Reviewer: gsd-code-reviewer (scoped)_
_Depth: standard_

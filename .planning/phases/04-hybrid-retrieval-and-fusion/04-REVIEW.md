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
  critical: 1
  warning: 0
  info: 0
  total: 1
status: issues_found
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

### CR-01: Query embedding capacity is exhausted permanently after 100 requests

**File:** `apps/worker/src/worker/query_embedding.py:50-65`

**Issue:** `max_requests` initializes `_remaining_requests` once for the lifetime of the long-lived worker listener, and every authenticated request decrements it before provider work. It is never replenished on a time window or process-independent rate limiter. With the configured default of 100, the 101st request and every later request receives `429 rate_limited` until the worker is restarted. The API treats this as an embedding failure and silently falls back to lexical-only retrieval, so normal production use permanently loses the dense channels without an operator-visible recovery path. This is reproducible with `max_requests=2`: two successful calls are followed by a third `429 rate_limited`.

**Fix:** Replace the lifetime counter with a time-based/token-bucket rate limiter (or explicitly use a concurrency-only bound if that is the intended control). Define a refill interval/configuration and add tests that prove capacity is restored after the interval and that failed/timed-out provider calls have the intended quota accounting semantics.

---

_Reviewed: 2026-08-11T00:00:00Z_
_Reviewer: the agent (gsd-code-reviewer)_
_Depth: standard_

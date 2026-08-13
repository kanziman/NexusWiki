---
phase: 04-hybrid-retrieval-and-fusion
plan: 05
subsystem: worker-boundary
tags: [query-embedding, token-bucket, monotonic-clock, rate-limiting]
requires:
  - phase: 04-01
    provides: private worker query-embedding boundary
provides:
  - bounded, monotonic-refilling query embedding capacity
  - explicit worker rate-limit configuration and accounting tests
affects: [retrieval, worker, private-api-boundary]
actuals:
  tokens: 4420
  tasks: 2
  commits: 2
tech-stack:
  added: []
  patterns: [lock-protected monotonic token bucket, deterministic injected-clock tests]
key-files:
  created: [apps/worker/tests/test_worker_main.py]
  modified:
    - apps/worker/src/worker/query_embedding.py
    - apps/worker/src/worker/settings.py
    - apps/worker/src/worker/__main__.py
    - apps/worker/tests/test_query_embedding.py
    - apps/worker/tests/test_settings.py
    - docs/architecture/query-embedding-boundary.md
key-decisions:
  - "Valid provider attempts consume a token even when they fail, time out, return malformed vectors, or are cancelled."
  - "Capacity and refill are explicit positive worker settings passed at startup rather than listener defaults."
requirements-completed: []
coverage:
  - id: D1
    description: Monotonic, capacity-capped token bucket restores query-embedding capacity after exhaustion.
    verification:
      - kind: unit
        ref: apps/worker/tests/test_query_embedding.py#test_token_bucket_refills_after_exhaustion_without_restart
        status: pass
      - kind: unit
        ref: apps/worker/tests/test_query_embedding.py#test_exhausted_bucket_admits_only_one_parallel_contender_after_refill
        status: pass
    human_judgment: false
  - id: D2
    description: Private-boundary authentication, validation, failure redaction, and provider-attempt quota accounting remain enforced.
    verification:
      - kind: unit
        ref: apps/worker/tests/test_query_embedding.py
        status: pass
      - kind: other
        ref: bash scripts/ci_check_query_embedding_boundary.sh
        status: pass
    human_judgment: false
  - id: D3
    description: Worker startup injects explicit configured rate capacity and refill values into the listener service.
    verification:
      - kind: unit
        ref: apps/worker/tests/test_worker_main.py#test_query_embedding_listener_receives_explicit_rate_settings
        status: pass
      - kind: unit
        ref: apps/worker/tests/test_settings.py#test_query_embedding_rate_settings_must_be_positive
        status: pass
    human_judgment: false
duration: 5 min
completed: 2026-08-11
status: complete
---

# Phase 04 Plan 05: Durable Query-Embedding Capacity Summary

**The worker’s private query-embedding listener now has a bounded monotonic token bucket that recovers capacity without weakening authentication, validation, redaction, or concurrency controls.**

## Performance

- **Duration:** 5 min
- **Started:** 2026-08-11T10:15:00Z
- **Completed:** 2026-08-11T10:20:38Z
- **Tasks:** 2/2
- **Files modified:** 7

## Accomplishments

- Replaced the process-lifetime request counter with a lock-protected, capacity-capped token bucket driven by injected `time.monotonic`.
- Added positive worker capacity/refill settings and explicitly supplies them to the production listener.
- Added deterministic coverage for refill, races, invalid requests, provider failures, timeouts, malformed vectors, cancellation, and startup configuration propagation.

## Task Commits

1. **Task 1: define and implement a monotonic token-bucket embedding request limit** — `6a14144` (feat)
2. **Task 2: prove durable capacity and retain every private-boundary safety contract** — `661fc20` (test)

## Files Created/Modified

- `apps/worker/src/worker/query_embedding.py` — token reservation, bounded refill, and attempted-provider accounting.
- `apps/worker/src/worker/settings.py` — positive rate capacity and refill settings.
- `apps/worker/src/worker/__main__.py` — explicit startup propagation of rate settings.
- `apps/worker/tests/test_query_embedding.py` — deterministic clock and accounting regression coverage.
- `apps/worker/tests/test_worker_main.py` — startup wiring regression test.
- `apps/worker/tests/test_settings.py` — rate-setting validation tests.
- `docs/architecture/query-embedding-boundary.md` — durable capacity and accounting decision record.

## Decisions Made

- A token is consumed for every authenticated, valid request that begins a provider attempt, including failure, timeout, malformed response, and cancellation; no token is refunded.
- Missing credentials and invalid text reserve no quota. Refills use monotonic elapsed time and never exceed configured capacity.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Verification

- `UV_CACHE_DIR=/tmp/nexuswiki-uv-cache uv run pytest -q apps/worker/tests/test_query_embedding.py apps/worker/tests/test_worker_main.py apps/worker/tests/test_settings.py` — 24 passed
- `UV_CACHE_DIR=/tmp/nexuswiki-uv-cache uv run ruff check apps/worker/src/worker/query_embedding.py apps/worker/src/worker/settings.py apps/worker/src/worker/__main__.py apps/worker/tests/test_query_embedding.py apps/worker/tests/test_worker_main.py` — passed
- `bash scripts/ci_check_query_embedding_boundary.sh` — passed

## Next Phase Readiness

Ready for the remaining Phase 04 gap-closure plans.

---
*Phase: 04-hybrid-retrieval-and-fusion*
*Completed: 2026-08-11*

---
phase: 05-citation-integrity-and-answer-apis
plan: 04
subsystem: worker
tags: [ask, llm, budget, usage-events]
requires:
  - phase: 05-citation-integrity-and-answer-apis
    provides: Private worker-owned LLM chat streaming listener
provides:
  - Monthly budget pre-flight checks before Ask opens an OpenRouter stream
  - One auditable usage-event write for every completed Ask stream
affects: [ask-api, worker, usage-events]
actuals:
  tasks: 2
  commits: 2
key-files:
  modified:
    - apps/worker/src/worker/db/service.py
    - apps/worker/src/worker/llm_stream.py
    - apps/worker/src/worker/__main__.py
    - apps/worker/src/worker/llm.py
    - apps/worker/tests/test_service_client.py
    - apps/worker/tests/test_llm_stream.py
    - apps/worker/tests/test_worker_main.py
requirements-completed: [API-01]
completed: 2026-08-12
status: complete
---

# Phase 05 Plan 04: Ask Budget Integrity Summary

**Ask now enforces the workspace's monthly cost cap before contacting OpenRouter and records each completed stream as a usage event.**

## Accomplishments

- Added workspace budget and UTC-window usage-sum read helpers; zero matching rows return `0` rather than a nullable value.
- Added an injected pre-flight budget check before rate reservation/provider invocation; usage equal to the cap returns HTTP 402.
- Captured terminal SSE usage safely and recorded one usage event after a normal stream completes, including an empty/$0 record when provider usage is absent.
- Reused the worker's ceil-to-micro-dollar cost conversion for Ask accounting.

## Task Commits

1. **Task 1: ServiceDb budget helpers** — `4f1cce9`
2. **Task 2: Ask budget gate and usage recording** — `85a1270`

## Verification

- `uv run pytest apps/worker/tests/test_service_client.py -x` — 21 passed
- `uv run pytest apps/worker/tests/test_service_client.py apps/worker/tests/test_llm_stream.py apps/worker/tests/test_worker_main.py -x` — 30 passed
- `uv run pytest` — 394 passed

## Deviations from Plan

None - plan executed exactly as written.

## Next Phase Readiness

The worker listener now exposes the cost-safety and audit guarantees needed by the remaining Phase 05 API and dashboard plans.

## Self-Check: PASSED

- `get_workspace_budget_cap()` and `sum_usage_events_since()` are classified table helpers with required keyword-only workspace scope.
- At-or-over-cap calls are rejected before the injected provider stream can run.
- Completed streams record exactly once, including malformed/incomplete streams that lack usage data.

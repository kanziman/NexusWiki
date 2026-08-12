---
phase: 05-citation-integrity-and-answer-apis
plan: 06
subsystem: worker
tags: [wiki, conflict-detection, embeddings, llm, job-queue]
requires:
  - phase: 05-citation-integrity-and-answer-apis
    provides: Similar-page RPC and completed wiki embedding pipeline
provides:
  - Write-time, candidate-bounded LLM conflict checking after wiki embedding
  - Automated disputed-state writes for both pages in a confirmed contradiction
  - Visible conflict-check job progress step
affects: [wiki, worker, jobs-api, citation-integrity]
actuals:
  tasks: 2
  commits: 2
key-files:
  created:
    - apps/worker/src/worker/handlers/conflict.py
  modified:
    - apps/worker/src/worker/db/service.py
    - apps/worker/src/worker/handlers/embed.py
    - apps/worker/src/worker/handlers/__init__.py
    - apps/api/src/api/routers/jobs.py
    - apps/worker/tests/test_handlers.py
    - apps/worker/tests/test_service_client.py
    - apps/api/tests/test_jobs_router.py
requirements-completed: [QC-01]
completed: 2026-08-12
status: complete
---

# Phase 05 Plan 06: Citation Integrity and Answer APIs Summary

**Each completed wiki embedding now triggers a bounded, write-time contradiction check that marks both genuinely conflicting pages disputed.**

## Accomplishments

- Added `find_similar_wiki_pages()` and `set_wiki_page_disputed()` ServiceDb helpers with explicit RPC/table-helper classification and workspace scoping.
- Added the `conflict_check` job handler: it reads only similarity-thresholded candidates, skips missing candidates, calls the structured LLM judge only when there is a candidate, and marks both pages only after a confirmed factual contradiction.
- Chained `conflict_check` after wiki-scope embedding only; source-scope embedding remains terminal. The jobs API now reports the named Korean progress step `지식 충돌 검사` at chain position 5.

## Task Commits

1. **Task 1: ServiceDb helpers for conflict candidates and disputed writes** — `370070b`
2. **Task 2: conflict_check handler, job-chain wiring, and job-status label** — `adaf324`

## Verification

- `uv run pytest apps/worker/tests/test_handlers.py -k conflict -x` — 3 passed
- `uv run pytest apps/worker/tests/test_handlers.py apps/worker/tests/test_service_client.py apps/api/tests/test_jobs_router.py -x` — 52 passed
- Full suite, run in test-path partitions because a single invocation exceeds the executor output window — 405 passed total: core 115, worker 142, API 148.

## Deviations from Plan

None - plan executed exactly as written.

## Next Phase Readiness

Phase 05's final QC-01 requirement is implemented. The existing dirty planning-state files were preserved because they predate this plan and are shared execution state for the phase orchestrator.

## Self-Check: PASSED

- A legitimate-variation result writes neither page; a confirmed contradiction writes both once.
- Zero semantic candidates produces zero structured LLM calls.
- The `source` embedding path still completes without a next job type.

---
phase: 05-citation-integrity-and-answer-apis
plan: 03
subsystem: api
tags: [citations, sse, ingest, rls, prompt-templates]
requires:
  - phase: 05-citation-integrity-and-answer-apis
    provides: Ask citation issuance and resolution path
provides:
  - Ingest-time forged-anchor removal before chunking
  - Per-answer citation quality metrics
  - RLS-scoped Ask template selection with silent fallback
affects: [05-04-PLAN, 05-06-PLAN, dashboard]
actuals:
  tokens: 6900
  tasks: 3
  commits: 3
tech-stack:
  added: []
  patterns:
    - Full-text sanitization before chunk offsets are calculated
    - RLS-hidden template selection falls back without existence disclosure
key-files:
  created:
    - packages/core/src/nexuswiki_core/sentences.py
    - packages/core/tests/test_sentences.py
    - apps/api/tests/test_ask_citations.py
  modified:
    - apps/worker/src/worker/handlers/parse.py
    - apps/api/src/api/services/ask.py
    - apps/api/src/api/routers/ask.py
key-decisions:
  - Forged anchors are stripped once from final extracted text before chunking.
  - Citation rates are computed once from the fully accumulated provider response.
  - Invalid or RLS-hidden template ids are indistinguishable and use the default template.
requirements-completed: [CITE-05, CITE-06, API-02]
coverage:
  - id: D1
    description: Ingested forged anchors are removed before chunks and offsets are made.
    requirement: CITE-06
    verification:
      - kind: unit
        ref: apps/worker/tests/test_handlers.py#test_parse_strips_forged_anchors_before_chunk_offsets_are_calculated
        status: pass
    human_judgment: false
  - id: D2
    description: Ask citation events report dual and unsourced sentence rates.
    requirement: CITE-05
    verification:
      - kind: unit
        ref: apps/api/tests/test_ask_citations.py#test_resolve_citations_reports_dual_and_unsourced_sentence_metrics
        status: pass
    human_judgment: false
  - id: D3
    description: Visible Ask templates are honored and hidden templates fall back silently.
    requirement: API-02
    verification:
      - kind: integration
        ref: apps/api/tests/test_ask_router.py#test_visible_requested_template_is_used_for_ask
        status: pass
    human_judgment: false
duration: 25min
completed: 2026-08-12
status: complete
---

# Phase 05 Plan 03: Citation Completion Summary

**Ask responses now measure citation coverage, ingested sources lose forged anchors before chunking, and callers can safely choose visible prompt templates.**

## Accomplishments

- Sanitized every source type at the common parse-to-chunk boundary while preserving post-strip offsets.
- Added stdlib-only Korean/English/mixed sentence splitting and four citation metrics to citations events.
- Added optional RLS-validated `template_id` selection with non-enumerating default fallback.

## Task Commits

1. **Task 1: strip forged anchors** — `aed5c41`
2. **Task 2: citation quality metrics** — `a52cd3c`
3. **Task 3: visible template selection** — `df41a12`

## Verification

- `uv run pytest packages/core/tests/test_sentences.py apps/api/tests/test_ask_citations.py apps/api/tests/test_ask_router.py apps/worker/tests/test_handlers.py -x` — 22 passed
- `uv run pytest -q` — 387 passed

## Deviations from Plan

None - plan executed exactly as written.

## Next Phase Readiness

Plans 05-04 and 05-05 can consume the completed Ask response and template-selection path.

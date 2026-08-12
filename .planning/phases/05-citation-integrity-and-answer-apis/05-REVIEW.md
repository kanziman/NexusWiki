---
phase: 05-citation-integrity-and-answer-apis
reviewed: 2026-08-12T00:09:25Z
depth: standard
files_reviewed: 34
files_reviewed_list:
  - apps/api/src/api/main.py
  - apps/api/src/api/routers/ask.py
  - apps/api/src/api/routers/graph.py
  - apps/api/src/api/routers/jobs.py
  - apps/api/src/api/routers/wiki.py
  - apps/api/src/api/services/ask.py
  - apps/api/src/api/settings.py
  - apps/api/tests/conftest.py
  - apps/api/tests/test_ask_citations.py
  - apps/api/tests/test_ask_router.py
  - apps/api/tests/test_graph_router.py
  - apps/api/tests/test_jobs_router.py
  - apps/api/tests/test_workspaces_isolation.py
  - apps/worker/src/worker/__main__.py
  - apps/worker/src/worker/db/service.py
  - apps/worker/src/worker/handlers/__init__.py
  - apps/worker/src/worker/handlers/conflict.py
  - apps/worker/src/worker/handlers/embed.py
  - apps/worker/src/worker/handlers/parse.py
  - apps/worker/src/worker/llm.py
  - apps/worker/src/worker/llm_stream.py
  - apps/worker/src/worker/query_embedding.py
  - apps/worker/src/worker/settings.py
  - apps/worker/tests/test_handlers.py
  - apps/worker/tests/test_llm_stream.py
  - apps/worker/tests/test_service_client.py
  - apps/worker/tests/test_settings.py
  - apps/worker/tests/test_worker_main.py
  - packages/core/src/nexuswiki_core/citations.py
  - packages/core/src/nexuswiki_core/sentences.py
  - packages/core/tests/test_citations.py
  - packages/core/tests/test_sentences.py
  - packages/core/tests/test_settings.py
  - supabase/migrations/0012_ask_citation_and_graph.sql
findings:
  critical: 0
  warning: 2
  info: 0
  total: 2
status: issues_found
---

# Phase 05: Code Review Report

**Reviewed:** 2026-08-12T00:09:25Z  
**Depth:** standard  
**Files Reviewed:** 34  
**Status:** issues_found

## Summary

Reviewed the Phase 05 Ask SSE path, private worker listener, citation integrity metrics, budget accounting, graph and verification APIs, conflict-detection chain, migration, and their direct tests. The request JWT boundary, citation alias resolution, and bounded graph inputs are consistently applied. Two correctness issues remain in the budget/audit paths.

## Findings

### Warning

#### WR-01 — Usage pagination silently lets high-volume workspaces bypass the monthly Ask cap

**Location:** `apps/worker/src/worker/db/service.py:457-468`

`sum_usage_events_since()` requests at most 1,000 rows and sums only that first page. PostgREST applies the limit before returning the response, so once a workspace has more than 1,000 usage events in the current month, every later event is omitted from the pre-flight `spent < cap` decision in `_check_ask_budget()`. The listener can then continue opening paid streams even when the actual monthly spend is already at or above the cap.

Replace this row fetch with a database aggregate/RPC, or paginate until exhaustion (with an explicit deterministic order) before making the cap comparison. Add coverage for a result set beyond the first page.

#### WR-02 — Automated dispute transitions overwrite the human verification audit fields

**Locations:** `apps/worker/src/worker/db/service.py:423-430`; `supabase/migrations/0012_ask_citation_and_graph.sql:195-200`

`set_wiki_page_disputed()` updates `verification_status` to `disputed`. That fires `wiki_pages_stamp_verification`, which unconditionally sets `verified_by := auth.uid()` and `verified_at := now()` for every status transition. Conflict checks run through the `service_role` path, where `auth.uid()` is not the prior human verifier (normally `NULL`), so a confirmed conflict replaces the page's existing human verification identity and timestamp. This contradicts the helper's stated intention not to touch those fields and loses the audit trail QC-02 is meant to preserve.

Make the trigger distinguish a requester JWT verification transition from an automated dispute transition, or record automated disputes in separate fields/event history while preserving the existing human-verification fields. Add an integration regression beginning with a verified page and asserting its audit fields survive a conflict-driven dispute.

## Verification

- `git diff --check e8e3555c..HEAD -- . ':(exclude).planning'` — passed.
- `uv run pytest apps/worker/tests/test_llm_stream.py apps/worker/tests/test_service_client.py apps/worker/tests/test_handlers.py apps/api/tests/test_ask_citations.py apps/api/tests/test_ask_router.py apps/api/tests/test_graph_router.py apps/api/tests/test_workspaces_isolation.py apps/api/tests/test_jobs_router.py packages/core/tests/test_citations.py packages/core/tests/test_sentences.py -x` — 89 passed.

---

_Reviewer: the agent (gsd-code-reviewer)_
_Depth: standard_

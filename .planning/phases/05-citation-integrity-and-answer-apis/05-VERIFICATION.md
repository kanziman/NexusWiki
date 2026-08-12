---
phase: 05-citation-integrity-and-answer-apis
verified: 2026-08-12T12:00:00+09:00
status: passed
score: 18/18 plan must-have truths verified; 12/12 phase requirements satisfied
behavior_unverified: 0
overrides_applied: 0
requirements:
  satisfied: [CITE-01, CITE-02, CITE-03, CITE-04, CITE-05, CITE-06, API-01, API-02, API-03, API-04, QC-01, QC-02]
  blocked: []
  needs_human: []
gaps: []
---

# Phase 5: Citation Integrity and Answer APIs Verification Report

**Phase goal:** Answers cite only evidence actually used by the model and remain traceable to both wiki and source records.

**Result:** `passed` — all Phase 05 requirements and plan must-have truths are implemented, regression-tested, and the two earlier safety gaps are closed.

## Goal achievement

| # | Roadmap success criterion | Status | Independent evidence |
| --- | --- | --- | --- |
| 1 | Short issued aliases; citations are parsed-anchor ∩ issued-map | ✓ VERIFIED | `ask.py` issues per-request `wN`/`sN` aliases and `resolve_citations()` intersects parsed aliases with the issuance map, rather than returning raw retrieval hits. Focused citation/SSE tests pass. |
| 2 | Forged aliases are removed and counted; no evidence returns the explicit message | ✓ VERIFIED | Broad anchors are stripped during parse before chunking; `AskService.ask()` short-circuits empty evidence with `근거를 찾지 못했습니다.` and no provider call. |
| 3 | Four citation metrics per answer; injected source anchors removed before prompt context | ✓ VERIFIED | Citation resolution returns both rates plus fabricated/cited counts; source parse strips forged anchors before `chunk_text()`. |
| 4 | POST SSE event order, selectable Ask templates, question-language behavior | ✓ VERIFIED | Ask returns a `StreamingResponse` and produces `meta`, zero-or-more `delta`, `citations`, then `done`; the RLS-scoped template selection and updated Ask seed prompts are present. |
| 5 | Read APIs, disputes, and verification audit preserve who/when/until | ✓ VERIFIED | Bounded graph, job, and wiki surfaces exist; conflict detection marks confirmed pairs disputed; the replacement trigger preserves a preceding human audit pair during service-role automation. |

**Roadmap score:** 5/5 success criteria verified.

## Requirement accounting

| Requirement | Status | Evidence |
| --- | --- | --- |
| CITE-01 | ✓ SATISFIED | Server-only `wN`/`sN` issuance and context blocks; real IDs are resolved only after model output. |
| CITE-02 | ✓ SATISFIED | `parsed_aliases & issuance.keys()` drives resolved citations, not the raw retrieval list. |
| CITE-03 | ✓ SATISFIED | Broad forged forms are stripped and non-issued narrow aliases are counted. |
| CITE-04 | ✓ SATISFIED | Empty retrieval skips the provider and emits the required Korean message. |
| CITE-05 | ✓ SATISFIED | Both citation rates and both counts are emitted in the citations event. |
| CITE-06 | ✓ SATISFIED | All source types converge on a pre-chunk broad-anchor strip. |
| API-01 | ✓ SATISFIED | Private worker listener plus POST SSE relay uses the fixed event ordering. |
| API-02 | ✓ SATISFIED | A visible requested Ask template is selected; unavailable IDs fall back to the default. |
| API-03 | ✓ SATISFIED | Seeded Ask prompts instruct the response to follow the question language. |
| API-04 | ✓ SATISFIED | Bounded graph RPC/router, wiki verification read surface, and existing source-job chain status are available. |
| QC-01 | ✓ SATISFIED | Bounded same-workspace embedding candidates are LLM-judged and confirmed conflicts mark both pages disputed. |
| QC-02 | ✓ SATISFIED | Editor transitions record DB-derived verifier/timestamp/expiry; a later service-role dispute retains the prior human `verified_by` and `verified_at`. |

**Requirements score:** 12/12 satisfied.

## Closure evidence for the prior gaps

### Ask monthly cap: complete aggregate and requester boundary

Migration `0013_ask_budget_and_verification_audit.sql` defines `public.sum_usage_events_since(uuid, timestamptz)` as `coalesce(sum(cost_micros), 0)` over every matching `usage_events` row. Its default execute privileges are revoked and execution is granted only to `service_role`. `ServiceDb.sum_usage_events_since()` calls that RPC directly, with no paginated table read, and `_check_ask_budget()` retains the inclusive `spent < cap` decision.

`test_local_budget_aggregate_is_complete_and_private` inserted 1,001 same-window events into the real local stack, received the complete total through the service-role client, proved a requester JWT is denied (401/403) at the RPC endpoint, and proved Ask preflight rejects when the cap equals that total. This explicitly covers both the former 1,000-row bypass and the requester privilege boundary.

### Automated dispute: durable human audit

The replacement `stamp_wiki_verification()` stamps `verified_by` and `verified_at` only when `auth.uid()` is a human requester. On an unauthenticated/service-role transition it instead copies `OLD.verified_by` and `OLD.verified_at`. `set_wiki_page_disputed()` remains the real service-role write used by `run_conflict_check()`.

`test_local_automated_dispute_retains_human_verification_audit` first creates a real requester-JWT `verified` transition, records its human audit pair, then drives a confirmed conflict through the production service-role dispute method. Both pages become `disputed`; the previously verified page retains the exact original `verified_by` and `verified_at` pair.

### Linked Supabase Cloud deployment evidence

`05-07-SUMMARY.md` records a successful `supabase db push --yes` of only migration `0013` to the already-linked remote, followed by `supabase db dump --linked --schema public`. The inspected live schema contained the aggregate RPC signature, its `service_role` execute grant, and the `OLD.verified_by` / `OLD.verified_at` preservation branch; the temporary dump was removed. This is deployment evidence, not an inferred local-only result.

## Automated verification performed

| Command | Result |
| --- | --- |
| `uv run pytest apps/worker/tests/test_queue.py apps/worker/tests/test_service_client.py apps/worker/tests/test_handlers.py apps/worker/tests/test_worker_main.py apps/api/tests/test_ask_citations.py apps/api/tests/test_ask_router.py apps/api/tests/test_graph_router.py apps/api/tests/test_workspaces_isolation.py apps/api/tests/test_jobs_router.py packages/core/tests/test_citations.py packages/core/tests/test_sentences.py -x -rs` | PASS — 109 passed. |
| `uv run pytest -q` | PASS — full suite completed successfully. Plan summary additionally records 408 passed immediately after the gap closure. |
| `git diff --check HEAD -- apps packages supabase .planning/phases/05-citation-integrity-and-answer-apis` | PASS. |

## Plan must-have assessment

All Plan 01–07 must-have truths are verified: 18/18. The former Plan 04 scale gap is closed by the database aggregate, and the former Plan 05/06 audit-preservation implication is closed by the replacement trigger and real local-stack integration test.

## Completion recommendation

Phase 05 may be marked complete. No implementation, safety, or verification gap remains.

---

_Verified: 2026-08-12T12:00:00+09:00_

_Verifier: Codex (GSD verifier)_

---
phase: 05-citation-integrity-and-answer-apis
verified: 2026-08-12T00:00:00+09:00
status: gaps_found
score: 16/18 plan must-have truths verified; 11/12 phase requirements satisfied
behavior_unverified: 0
overrides_applied: 0
requirements:
  satisfied: [CITE-01, CITE-02, CITE-03, CITE-04, CITE-05, CITE-06, API-01, API-02, API-03, API-04, QC-01]
  blocked: [QC-02]
  needs_human: []
gaps:
  - "The conflict-check service-role transition overwrites verified_by/verified_at through the verification trigger, losing the previous human audit identity and timestamp (QC-02)."
  - "Ask monthly-cap accounting reads only the first 1,000 usage_events, so a high-volume workspace can pass the preflight budget check after its actual cap is reached."
---

# Phase 5: Citation Integrity and Answer APIs Verification Report

**Phase goal:** 답변이 실제로 사용한 근거만 인용하고, 위키와 원문 양쪽으로 추적된다.

**Result:** `gaps_found` — citation integrity, Ask SSE, read APIs, and write-time conflict detection are implemented and tested. Two review-confirmed correctness gaps prevent completion: QC-02's human verification audit can be overwritten by automated disputes, and the Phase 05 Ask budget cap only sums the first 1,000 events.

## Goal achievement

| # | Roadmap success criterion | Status | Independent evidence |
| --- | --- | --- | --- |
| 1 | Short issued aliases; citations are parsed-anchor ∩ issued-map | ✓ VERIFIED | `ask.py:118-134` creates only `wN`/`sN` aliases; `resolve_citations()` intersects parsed aliases with `issuance` (`147-189`). The focused citation/SSE tests passed. |
| 2 | Forged aliases are removed and counted; no evidence returns the explicit message | ✓ VERIFIED | Broad anchors are stripped in `citations.py` and `parse.py` before chunking; `AskService.ask()` short-circuits empty evidence to `근거를 찾지 못했습니다.` (`366-382`). |
| 3 | Four citation metrics per answer; injected source anchors removed before prompt context | ✓ VERIFIED | `resolve_citations()` returns both ratios and both counts; parse applies `strip_forged_anchors()` before `chunk_text()`. |
| 4 | POST SSE event order, selectable Ask templates, question-language behavior | ✓ VERIFIED | Ask router returns `StreamingResponse`; service emits `meta`, zero-or-more `delta`, `citations`, `done` (`414-489`). RLS-scoped template selection and migration 0012's language/alias instruction are present. |
| 5 | Read APIs, disputes, and verification audit preserve who/when/until | ✗ GAP | Graph/job/wiki APIs and write-time conflict check exist, but automated `disputed` transitions overwrite the preceding human verifier audit fields (QC-02 gap below). |

**Roadmap score:** 4/5 success criteria verified.

## Requirement accounting

| Requirement | Status | Evidence |
| --- | --- | --- |
| CITE-01 | ✓ SATISFIED | Server-only `wN`/`sN` issuance and context blocks; real IDs are resolved only after model output. |
| CITE-02 | ✓ SATISFIED | `parsed_aliases & issuance.keys()` drives `resolved`, not the raw retrieval list. |
| CITE-03 | ✓ SATISFIED | Broad forged forms are removed and non-issued narrow aliases counted. |
| CITE-04 | ✓ SATISFIED | Empty retrieval skips the provider and emits the required Korean message. |
| CITE-05 | ✓ SATISFIED | Both citation rates and both counts are emitted in the citations event. |
| CITE-06 | ✓ SATISFIED | All source types converge on a pre-chunk broad-anchor strip. |
| API-01 | ✓ SATISFIED | Private worker listener plus POST SSE relay with fixed event ordering; focused worker/API tests pass. |
| API-02 | ✓ SATISFIED | Requested template is RLS-read; hidden/invalid IDs silently fall back to default. |
| API-03 | ✓ SATISFIED | The corrected seeded Ask prompts instruct response language to follow the question. |
| API-04 | ✓ SATISFIED | Bounded graph RPC/router, wiki verification read surface, and existing job-status chain are present; conflict step is surfaced. |
| QC-01 | ✓ SATISFIED | Wiki embedding chains `conflict_check`; bounded same-workspace candidates are LLM-judged and both confirmed pages become disputed. |
| QC-02 | ✗ GAP | User verification endpoint and DB trigger record fields initially, but a subsequent automated conflict transition destroys the prior human audit record. |

**Requirements score:** 11/12 satisfied.

## Required gaps

### GAP-01 — QC-02 audit fields are overwritten by automated disputes

`ServiceDb.set_wiki_page_disputed()` intentionally changes `verification_status` to `disputed` without supplying audit fields (`apps/worker/src/worker/db/service.py:414-430`), and the conflict handler calls it for both pages (`apps/worker/src/worker/handlers/conflict.py:104-108`). Migration `0012`'s `stamp_wiki_verification()` trigger unconditionally sets `new.verified_by := auth.uid()` and `new.verified_at := now()` on *every* status change (`supabase/migrations/0012_ask_citation_and_graph.sql:193-205`). In the service-role conflict path, that replaces the prior human verifier/timestamp (normally with a non-human/null identity), contradicting the helper's documented intent and QC-02's durable “who/when/until” audit requirement.

**Closure needed:** distinguish authenticated human verification transitions from automated disputes in the trigger/write model, or store automated dispute history separately while preserving the prior human verification fields. Add a regression that starts with a human-verified page, runs a confirmed conflict, and asserts `verified_by` and `verified_at` remain intact.

### GAP-02 — Ask monthly cap is bypassable after 1,000 usage events

`sum_usage_events_since()` selects `usage_events` with `limit=1000` and sums only that returned page (`apps/worker/src/worker/db/service.py:457-468`). The Ask listener uses that value as its preflight monthly-cap decision. A workspace with more than 1,000 events in the window omits later spend and can open billable streams after the real cap is reached.

**Closure needed:** use a database aggregate/RPC, or deterministically paginate to exhaustion before comparing spend to the cap; add a >1,000-row regression test.

## Automated verification performed

| Command | Result |
| --- | --- |
| `uv run pytest apps/worker/tests/test_llm_stream.py apps/worker/tests/test_service_client.py apps/worker/tests/test_handlers.py apps/api/tests/test_ask_citations.py apps/api/tests/test_ask_router.py apps/api/tests/test_graph_router.py apps/api/tests/test_workspaces_isolation.py apps/api/tests/test_jobs_router.py packages/core/tests/test_citations.py packages/core/tests/test_sentences.py -x` | PASS — 89 passed |
| `uv run pytest -q` | PASS — 405 tests; command exited 0 (executor output stream truncated after progress rendering) |
| `git diff --check HEAD -- apps packages supabase .planning/phases/05-citation-integrity-and-answer-apis` | PASS |

## Plan must-have assessment

All Plan 01/02/03/05/06 truth statements are verified except the QC-02 audit preservation implication. Plan 04's first-1,000-row usage read also fails its stated budget-cap truth at scale. Thus 16/18 plan must-have truths are verified, with no behavior left merely untested.

## Gaps summary

Do not mark Phase 05 complete yet. The citation and API core are ready, but the two concrete gaps above need closure and regression coverage before the phase can truthfully claim durable verification audit and reliable Ask spend enforcement.

---

_Verified: 2026-08-12T00:00:00+09:00_

_Verifier: Codex (GSD verifier)_

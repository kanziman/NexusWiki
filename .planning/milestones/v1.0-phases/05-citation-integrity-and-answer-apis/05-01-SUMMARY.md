---
phase: 05-citation-integrity-and-answer-apis
plan: 01
subsystem: api
tags: [fastapi, httpx, sse, streaming, openrouter, pydantic, citation-integrity]

# Dependency graph
requires:
  - phase: 04-hybrid-retrieval-and-fusion
    provides: "RetrievalService.retrieve() -> RetrievalResult(evidence, meta) — Phase 5's only input from Phase 4"
  - phase: 02-security-spine-and-shared-domain
    provides: "worker-owned-secret / private-network relay pattern (query-embedding boundary), BaseAppSettings/ApiSettings/WorkerSettings split"
provides:
  - "Worker-owned private /internal/llm-chat streaming listener (D-01 boundary), sharing one FastAPI app/uvicorn.Server with the existing query-embedding listener"
  - "packages/core two-regex citation anchor grammar (BROAD_ANCHOR_PATTERN strip-time, ISSUED_ANCHOR_PATTERN parse-time)"
  - "AskService citation issuance/resolution (build_issuance_map, resolve_citations) implementing CITE-01/02/03"
  - "POST /workspaces/{id}/ask SSE endpoint: meta -> delta* -> citations -> done, with CITE-04 empty-evidence short-circuit"
affects: [05-02, 05-03, 05-04, 05-05, phase-06-ask-ui]

# Actuals (#2632)
actuals:
  tokens: 15138
  tasks: 2
  commits: 2

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "worker-owned-secret + private-network relay (D-01): second route on the same worker FastAPI app/uvicorn.Server, not a second port"
    - "auth/rate-limit checks that must produce a clean HTTP status live in a plain coroutine awaited BEFORE StreamingResponse is constructed — never inside the async-generator body that becomes the response's body_iterator (Starlette sends `http.response.start` before the first body chunk is pulled; verified empirically, see Deviations)"
    - "two-regex citation anchor grammar: broad strip-time pattern (CITE-06 substrate) vs narrow issued-time pattern (CITE-01/02/03)"
    - "framing-agnostic service generator yielding (event_name, payload) tuples + router-owned SSE string rendering, so citation-resolution logic is testable independent of wire format"

key-files:
  created:
    - apps/worker/src/worker/llm_stream.py
    - apps/api/src/api/services/ask.py
    - apps/api/src/api/routers/ask.py
    - packages/core/src/nexuswiki_core/citations.py
    - apps/worker/tests/test_llm_stream.py
    - apps/api/tests/test_ask_router.py
    - packages/core/tests/test_citations.py
  modified:
    - apps/worker/src/worker/llm.py
    - apps/worker/src/worker/query_embedding.py
    - apps/worker/src/worker/__main__.py
    - apps/worker/src/worker/settings.py
    - apps/api/src/api/settings.py
    - apps/api/src/api/main.py
    - apps/worker/tests/test_settings.py
    - apps/worker/tests/test_worker_main.py
    - packages/core/tests/test_settings.py

key-decisions:
  - "Starlette's StreamingResponse sends `http.response.start` (status 200) before iterating the body — verified empirically with a standalone probe. Raising HTTPException from inside an async-generator `stream()` method (as the plan's literal sketch specified) produces `RuntimeError: Caught handled exception, but response already started`, not a clean 401/429. Fixed by splitting LlmStreamService.stream() into a plain-coroutine auth+quota-reservation step (awaited by the router before constructing StreamingResponse) and a separate pure-generator chunk relay."
  - "AskService.ask() keeps retrieve() + evidence-check + LLM streaming inside one async generator (matching the plan's design) — this is safe because it never needs to change the top-level HTTP status: the router pre-validates query length (mirroring retrieval.py's 422 check) and AskRequest.requested_k's Pydantic bound (1..8) matches DEFAULT_RETRIEVAL_POLICY.requested_k exactly, so retrieve() cannot raise ValueError for a validated request. Every remaining failure mode (no evidence, LLM non-2xx, LLM transport failure) is a legitimate SSE-level `citations` event under a 200 status per D-03's design, not a different HTTP status — so the Task-1-style generator-timing bug does not apply here."
  - "_fetch_evidence_content()/_select_default_ask_template() reuse jobs.py::_usage_rows_since's narrow UserDb._client/_base_url/_headers/_payload seam (with `# noqa: SLF001`) instead of adding new UserDb methods — UserDb.select()'s public filter is eq-only and can't express `in.(...)` or `workspace_id is.null`; the global-template lookup filters client-side for `workspace_id is None` on RLS-scoped rows instead."

patterns-established:
  - "Pattern: separate 'must-produce-clean-HTTP-status' work (coroutine, awaited pre-StreamingResponse) from 'this-is-just-an-SSE-event' work (generator) — apply this test before writing any new streaming-response service method."
  - "Pattern: framing-agnostic (event_name, payload) tuple generator in the service + a router-local `_format_sse()` renderer, so citation/event-order logic is unit-testable without parsing SSE text."

requirements-completed: [CITE-01, CITE-02, CITE-03, CITE-04, API-01, API-03]

coverage:
  - id: D1
    description: "Worker-owned private /internal/llm-chat listener: authenticates bearer token before any provider work, enforces a monotonic token-bucket rate limit, relays a live OpenRouter streaming completion as raw SSE bytes, and shares one FastAPI app/uvicorn.Server with the existing query-embedding listener (D-01)."
    requirement: API-01
    verification:
      - kind: unit
        ref: "apps/worker/tests/test_llm_stream.py::test_unauthenticated_request_is_rejected_before_any_provider_call"
        status: pass
      - kind: unit
        ref: "apps/worker/tests/test_llm_stream.py::test_authenticated_request_relays_injected_bytes_unchanged"
        status: pass
      - kind: unit
        ref: "apps/worker/tests/test_llm_stream.py::test_exhausted_token_bucket_returns_429_without_calling_chat_stream"
        status: pass
    human_judgment: false
  - id: D2
    description: "Two-regex citation anchor grammar: ISSUED_ANCHOR_PATTERN matches only the server-issued alias shape ([[wiki:w1]]/[[src:s1]]); BROAD_ANCHOR_PATTERN matches any bracket-anchor-shaped text and strip_forged_anchors() removes it (CITE-01 substrate; call-site wiring for CITE-06 is 05-03-PLAN.md)."
    requirement: CITE-01
    verification:
      - kind: unit
        ref: "packages/core/tests/test_citations.py::test_issued_pattern_matches_the_exact_alias_shape_this_server_issues"
        status: pass
      - kind: unit
        ref: "packages/core/tests/test_citations.py::test_issued_pattern_rejects_a_real_slug_or_id_instead_of_an_alias"
        status: pass
      - kind: unit
        ref: "packages/core/tests/test_citations.py::test_broad_pattern_matches_both_issued_aliases_and_forged_shapes"
        status: pass
      - kind: unit
        ref: "packages/core/tests/test_citations.py::test_strip_forged_anchors_removes_anything_broad_shaped"
        status: pass
    human_judgment: false
  - id: D3
    description: "Citations are computed as parsed-anchor ∩ server-issued-alias-map (never the raw retrieval evidence list, CITE-02); a parsed anchor absent from the issuance map is counted as fabricated and stripped from the rendered text (CITE-03)."
    requirement: CITE-02
    verification:
      - kind: unit
        ref: "apps/api/tests/test_ask_router.py::test_grounded_answer_streams_meta_delta_citations_done_with_fabrication_stripped"
        status: pass
    human_judgment: false
  - id: D4
    description: "A query with zero retrieval evidence streams meta -> citations{text=NO_EVIDENCE_MESSAGE} -> done with zero calls made to the worker LLM-stream client (CITE-04, no provider spend)."
    requirement: CITE-04
    verification:
      - kind: unit
        ref: "apps/api/tests/test_ask_router.py::test_no_evidence_short_circuits_before_any_llm_call"
        status: pass
    human_judgment: false
  - id: D5
    description: "POST /workspaces/{id}/ask streams SSE events in the exact order meta -> delta* -> citations -> done for a grounded query, calling Task 1's /internal/llm-chat over the private network."
    requirement: API-01
    verification:
      - kind: unit
        ref: "apps/api/tests/test_ask_router.py::test_grounded_answer_streams_meta_delta_citations_done_with_fabrication_stripped"
        status: pass
    human_judgment: false
  - id: D6
    description: "Answer language follows question language — implemented structurally (question text passed verbatim into the rendered user prompt; the workspace's default ask system prompt already carries the language-following instruction per D-08) rather than a separate translation pass. No live LLM call was made this task, so language-following itself is unverified by any automated test."
    requirement: API-03
    verification: []
    human_judgment: true
    rationale: "Verifying that answers actually follow the question's language requires a live OpenRouter call and human/LLM-judge evaluation of the response text — out of reach for this task's fully-offline test suite (no live provider key exercised). Structural wiring (question flows into the prompt unmodified, existing system-prompt instruction reused unchanged) is complete; behavioral verification is deferred to a later manual/UAT pass once a real LLM call is exercised (Phase 6 UI or a dedicated smoke test)."

duration: 35min
completed: 2026-08-12
status: complete
---

# Phase 5 Plan 1: Worker LLM-Streaming Listener + Citation-Integrity Ask API Summary

**Worker-owned `/internal/llm-chat` streaming listener plus `POST /workspaces/{id}/ask` — SSE-streamed, dual-cited answers where citations are computed as parsed-anchor ∩ server-issued-alias-map, never the raw retrieval list.**

## Performance

- **Duration:** ~35 min
- **Tasks:** 2 (Task 1: tracer, Task 2: expansion)
- **Files modified:** 16 (8 new, 8 modified — no overlap between tasks)

## Accomplishments

- Worker now exposes a second private route (`/internal/llm-chat`) on the same FastAPI app/`uvicorn.Server` as the existing query-embedding listener — proves the D-01 worker-owned-secret / API-relay boundary end-to-end, on real streaming HTTP, before any expansion work builds on it.
- `packages/core/src/nexuswiki_core/citations.py` gives the whole codebase one shared, tested two-regex anchor grammar (broad strip-time vs. narrow issued-time) — 05-03's forged-anchor-stripping wiring has zero new regex design work left.
- `POST /workspaces/{id}/ask` is a real, callable endpoint: a workspace member with a JWT gets a correctly-ordered SSE stream (`meta` → `delta*` → `citations` → `done`) whose citations are the intersection of what the model actually wrote and what the server actually issued — and a zero-evidence query gets an explicit, zero-cost `근거를 찾지 못했습니다.` refusal instead of a fabricated answer or a hang.

## Task Commits

1. **Task 1: Worker-owned private LLM-streaming listener** - `5364c54` (feat)
2. **Task 2: Citation anchor issuance/resolution + Ask API wired to Task 1's listener** - `6e6495e` (feat)

**Plan metadata:** (this commit, following SUMMARY.md creation)

## Files Created/Modified

- `apps/worker/src/worker/llm_stream.py` - New `LlmStreamService`/`add_llm_stream_route` — auth-before-quota, token-bucket rate limiter, streaming relay
- `apps/worker/src/worker/llm.py` - Added `stream_chat()`/`_chat_stream_body()`, sibling of `complete_structured()`
- `apps/worker/src/worker/query_embedding.py` - Extracted `add_query_embedding_route()` so both routes share one app
- `apps/worker/src/worker/__main__.py` - `_serve_query_embeddings` → `_serve_internal_listeners`, wires both routes onto one `uvicorn.Server`
- `apps/worker/src/worker/settings.py` - `LLM_STREAM_INTERNAL_TOKEN`/`_MAX_CONCURRENCY`/`_RATE_CAPACITY`/`_RATE_REFILL_TOKENS_PER_SECOND`
- `packages/core/src/nexuswiki_core/citations.py` - `BROAD_ANCHOR_PATTERN`/`ISSUED_ANCHOR_PATTERN`/`strip_forged_anchors()`
- `apps/api/src/api/services/ask.py` - New `AskService`, `HttpLlmStreamClient`, `build_issuance_map()`, `resolve_citations()`
- `apps/api/src/api/routers/ask.py` - `POST /workspaces/{id}/ask`, `_format_sse()` framing
- `apps/api/src/api/settings.py` - `LLM_STREAM_INTERNAL_URL`/`_TOKEN`/`_TIMEOUT_SECONDS`
- `apps/api/src/api/main.py` - Wired `ask_router` into `create_app()`
- `apps/worker/tests/test_llm_stream.py`, `apps/worker/tests/test_settings.py`, `apps/worker/tests/test_worker_main.py` - Task 1 coverage
- `apps/api/tests/test_ask_router.py`, `packages/core/tests/test_citations.py`, `packages/core/tests/test_settings.py` - Task 2 coverage

## Decisions Made

- Split `LlmStreamService.stream()` into a plain-coroutine auth/quota step (awaited before `StreamingResponse` is constructed) and a separate pure-generator chunk relay, after empirically confirming Starlette sends `http.response.start` before pulling the first body chunk — see Deviations below.
- Kept `AskService.ask()` as one all-in-one async generator (matching the plan's literal design) since none of its internal failure paths need a non-200 top-level HTTP status — router-level query-length pre-validation and matching Pydantic/policy bounds mean `retrieve()` never raises inside the generator.
- Reused `jobs.py::_usage_rows_since`'s narrow `UserDb._client`/`_base_url`/`_headers`/`_payload` seam for the `in.(...)` evidence-content fetch and the `workspace_id is.null` global-template fallback, rather than growing `UserDb`'s public surface.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed the plan's literal async-generator auth pattern for `/internal/llm-chat`**
- **Found during:** Task 1, while writing Test 1 (unauthenticated request must be rejected 401 before any provider call)
- **Issue:** The plan's action text and 05-RESEARCH.md's Pattern 1 code sketch both put the `authorization != f"Bearer ..."` check and `raise HTTPException(401, ...)` directly inside `LlmStreamService.stream()`, an `async def` method containing `yield` (i.e., an async generator). `StreamingResponse` sends the ASGI `http.response.start` event (status 200) before ever pulling the first item from its body iterator (verified directly against installed `starlette==1.3.1` source and a standalone probe script). Raising inside the generator body therefore happens *after* the 200 has already gone out, producing `RuntimeError: Caught handled exception, but response already started` instead of a clean 401 — Test 1 would fail with a broken connection, not an assertable status code.
- **Fix:** Split `LlmStreamService.stream()` into a plain coroutine (no `yield`) that does the `Bearer` check and `_reserve_token()` call and returns a separate pure-generator (`_stream_chunks()`) for the actual byte relay. The router now does `chunks = await service.stream(request, authorization); return StreamingResponse(chunks, ...)` — the exception now happens *before* `StreamingResponse` is ever constructed, so FastAPI's normal exception-handling path renders 401/429 correctly.
- **Files modified:** `apps/worker/src/worker/llm_stream.py`
- **Verification:** `apps/worker/tests/test_llm_stream.py::test_unauthenticated_request_is_rejected_before_any_provider_call` and `::test_exhausted_token_bucket_returns_429_without_calling_chat_stream` both pass, asserting the real HTTP status codes.
- **Committed in:** `5364c54` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Necessary for Test 1/Test 3's acceptance criteria ("rejected 401 before any OpenRouter call", "returns 429") to be literally true rather than a broken streaming connection. No scope creep — the plan's stated *contract* (auth before work, 401/429 status codes) is unchanged; only the internal generator/coroutine split needed to actually deliver that contract over `StreamingResponse`.

## Issues Encountered

None beyond the deviation above — both tasks' `<verify>` commands passed on the first real run once the Task 1 fix landed, and the full monorepo suite (`uv run pytest`, 380 tests) is green with the local Supabase stack up (no skips).

## User Setup Required

None - no external service configuration required. (`LLM_STREAM_INTERNAL_TOKEN`/`LLM_STREAM_INTERNAL_URL` are new optional settings with `None` defaults on both worker and API; production Railway env-var provisioning for these is an operational task, not a code dependency of this plan.)

## Next Phase Readiness

- The tracer bullet is proven end-to-end: a real workspace member can call `POST /workspaces/{id}/ask` today and get a real, dual-citation-resolved streamed answer for both the grounded and no-evidence paths.
- Ready for 05-02 (same wave — migration `0012` updating the seeded `ask` prompt templates' citation instruction text to match the `[[wiki:w1]]` alias scheme, D-10) and 05-03 (CITE-05 metrics on `resolve_citations()`, CITE-06 `strip_forged_anchors()` call-site wiring in `worker/handlers/parse.py`, API-02 `template_id` override).
- Explicitly deferred, not stubbed: `template_id` override (API-02, always uses the workspace default template this plan), Ask-path budget-cap enforcement (D-09, 05-04-PLAN.md), CITE-05's two ratio metrics (05-03-PLAN.md). Each has a named owner plan in `05-CONTEXT.md`/`05-RESEARCH.md` — none are silent gaps.
- API-03 (answer-language-follows-question) is structurally wired but behaviorally unverified by any automated test this plan (see coverage `D6`) — no live OpenRouter call was exercised. Flagged for human/UAT verification once Phase 6's UI or a dedicated smoke test exercises a real provider call.

---
*Phase: 05-citation-integrity-and-answer-apis*
*Completed: 2026-08-12*

## Self-Check: PASSED

All 8 created/modified files verified present on disk; both task commits (`5364c54`, `6e6495e`) verified present in `git log --all`.

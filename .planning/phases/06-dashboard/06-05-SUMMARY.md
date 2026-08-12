---
phase: 06-dashboard
plan: 05
subsystem: ui
tags: [nextjs, radix-ui, react, vitest, tdd, apps-api]

requires:
  - phase: 06-dashboard
    provides: "06-01: workspacePath/@supabase/ssr client factories, middleware tenancy gate; 06-04: lib/api-client.ts apiFetch/ApiError authenticated fetch wrapper"
provides:
  - "apps/dashboard/components/Dropzone.tsx — 3-tab (file/URL/text) source ingest, raw-bytes file upload, dedup/budget/mime error-copy mapping"
  - "apps/dashboard/components/JobStepper.tsx — real 5-stage job-chain progress (3s poll), dead-job retry, cancel-with-confirm"
  - "apps/dashboard/components/SourcesList.tsx — client wrapper coordinating Dropzone + per-source JobStepper, targeted-row prepend on ingest"
  - "apps/dashboard/app/w/[workspaceId]/sources/page.tsx — /sources route, Server Component RLS read (raw_sources, no content column, limit 50)"
affects: [06-06 (ask ui may link back to sources), 06-07 (wiki verify action, no direct dependency)]

actuals:
  tokens: 10480
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "userEvent (not fireEvent.click) required for Radix Tabs activation in jsdom tests — Radix's default automatic activationMode fires on focus, which fireEvent.click does not simulate"
    - "getByLabelText collisions with Radix's aria-labelledby-on-tabpanel: a form label whose text equals its own tab trigger's visible text becomes ambiguous under getByLabelText; disambiguate with a slightly longer label string"
    - "onIngested(jobId, rawSourceId) two-arg callback + targeted single-row Supabase select (not a full list refetch) to prepend a newly-ingested source without waiting for a full page reload"

key-files:
  created:
    - apps/dashboard/components/Dropzone.tsx
    - apps/dashboard/tests/Dropzone.test.tsx
    - apps/dashboard/components/JobStepper.tsx
    - apps/dashboard/tests/JobStepper.test.tsx
    - apps/dashboard/components/SourcesList.tsx
    - apps/dashboard/app/w/[workspaceId]/sources/page.tsx
  modified: []

key-decisions:
  - "JobStepper's 5 header captions (업로드/파싱/컴파일/링크 동기화/임베딩) are a separate, hardcoded, D-05-verbatim string set — NOT a duplicate of jobs.py's STEP_LABELS map. STEP_LABELS (fuller server strings like '원문 파싱') is consumed only for the dead-job error-message template's {단계} substitution, per the plan's own read_first instruction not to re-derive that map client-side."
  - "SourcesList.tsx's onIngested handler does a single targeted Supabase select (.eq('id', rawSourceId).single()) instead of refetching the full 50-row list, since Dropzone's fixed 2-arg callback signature (jobId, rawSourceId) carries no title/source_type/created_at — and sources.py's _insert_and_enqueue already commits the raw_sources row before returning 202, so the row is guaranteed to exist by the time apiFetch resolves."
  - "Dropzone's URL-tab label text was changed from bare 'URL' to 'URL 주소' to avoid a getByLabelText ambiguity: Radix sets aria-labelledby on the tabpanel pointing at the trigger button (whose own text is also 'URL'), so a same-text form label collides with it under label-based queries."

patterns-established:
  - "Radix Tabs test interaction: always use @testing-library/user-event's user.click on the tab trigger (never fireEvent.click) since automatic activationMode switches tabs on focus, not on a bare click event"

requirements-completed: [UI-03]

coverage:
  - id: D1
    description: "Dropzone renders 3 tabs (file/URL/text) in one component (D-06); file tab sends raw File bytes (never FormData/multipart) with the file's own MIME as Content-Type; URL tab client-pre-validates http(s) scheme before any request; text tab submit stays disabled while empty"
    requirement: UI-03
    verification:
      - kind: unit
        ref: "apps/dashboard/tests/Dropzone.test.tsx — 7 tests, all pass"
        status: pass
    human_judgment: false
  - id: D2
    description: "409 already_ingested / 402 budget_exceeded / 422 invalid_source(unsupported_mime) each render the exact UI-SPEC copy string, and the MIME rejection case never echoes the raw Content-Type back to the user"
    requirement: UI-03
    verification:
      - kind: unit
        ref: "apps/dashboard/tests/Dropzone.test.tsx — 3 error-mapping tests, all pass"
        status: pass
    human_judgment: false
  - id: D3
    description: "JobStepper renders the real 5-stage sequence (업로드→파싱→컴파일→링크 동기화→임베딩) from live jobs.py data, highlights the current queued/running stage, never renders an indeterminate spinner (ING-06)"
    requirement: UI-03
    verification:
      - kind: unit
        ref: "apps/dashboard/tests/JobStepper.test.tsx — 5-stage/current-stage test, pass"
        status: pass
      - kind: other
        ref: "grep -c 'spinner\\|Spinner' apps/dashboard/components/JobStepper.tsx == 0"
        status: pass
    human_judgment: false
  - id: D4
    description: "Dead jobs expose a 44x44px aria-label='재시도' retry button wired to the retry endpoint; non-terminal jobs expose a cancel affordance whose confirmation dialog shows the exact required cost-non-refund disclosure on every occurrence (only cancel affordance in this plan)"
    requirement: UI-03
    verification:
      - kind: unit
        ref: "apps/dashboard/tests/JobStepper.test.tsx — retry-button and cancel-dialog-copy tests, pass"
        status: pass
    human_judgment: false
  - id: D5
    description: "sources/page.tsx (Server Component) reads raw_sources via RLS (raw_sources_select_member), excludes the content column, caps at 50 rows, and renders the exact empty-state copy when the list is empty; SourcesList prepends newly-ingested sources without a full list refetch"
    requirement: UI-03
    verification:
      - kind: other
        ref: "pnpm exec tsc --noEmit (clean) + pnpm exec next build (succeeds, /w/[workspaceId]/sources route present)"
        status: pass
    human_judgment: false
  - id: D6
    description: "Full end-to-end click-through against a running apps/api + supabase start + worker: file/URL/text ingest each produce a visible job chain progressing through real stages"
    verification: []
    human_judgment: true
    rationale: "No apps/api, worker, or next dev process was running in this session (only the local Supabase Docker stack was up); starting all three plus creating throwaway auth/workspace fixtures and triggering a real LLM compile call was out of scope for this execution given cost/time — same class of gap 06-01/06-02/06-03 documented for RSC/middleware/RLS live behavior. A future session must run this live pass before relying on it as proven."
  - id: D7
    description: "Source list shows skeleton rows on initial fetch before data resolves (UI-SPEC backstop truth)"
    verification: []
    human_judgment: true
    rationale: "Task 3's own <action> mandates an SSR-first fetch (Server Component resolves the initial 50 rows before the page ships), so there is no client-side 'initial fetch' phase for the outer list — data always arrives pre-resolved with the HTML. This architecturally satisfies the intent (no spinner ever flashes for stale/loading list state) but does not literally implement a loading-skeleton branch for the list itself, unlike JobStepper's own per-source polling loading state. Flagging for human sign-off rather than silently marking covered."

duration: ~1h
completed: 2026-08-12
status: complete
---

# Phase 6 Plan 5: Dropzone and Job Progress Summary

**Real 3-tab source ingest (file/URL/text, raw-bytes upload, D-06) wired to a live 5-stage job-chain stepper (D-05) with dead-job retry and cost-disclosure cancel confirmation (D-08), backing the `/sources` route with an SSR-first, RLS-scoped source list.**

## Performance

- **Duration:** ~1h
- **Tasks:** 3/3 completed
- **Files created:** 6 (4 source, 2 test)

## Accomplishments

- `Dropzone.tsx`: Radix Tabs 3-tab ingest UI reusing `06-04`'s `apiFetch`/`ApiError`. File tab sends the raw `File` object as the request body (never `FormData`/multipart), matching `sources.py`'s raw-bytes contract (D-P11) exactly, with the file's own `type` as `Content-Type` via `apiFetch`'s `contentType` escape hatch. URL tab pre-validates `http(s)` scheme client-side before any request. Text tab gates submit on non-empty title+text (mirrors backend `min_length=1`). Maps `ApiError` 409/402/422 cases to the exact UI-SPEC copy strings, with the 422 `unsupported_mime` case deliberately never echoing the raw MIME string.
- `JobStepper.tsx`: polls `GET /workspaces/{id}/sources/{id}/jobs` every 3s and renders the fixed D-05 5-stage caption sequence (a hardcoded UI-copy set, distinct from and not duplicating `jobs.py`'s server-owned `STEP_LABELS` map, which is consumed only for the dead-row error template). Highlights the first `queued`/`running` stage as current. Dead rows get a 44×44px `aria-label="재시도"` retry button plus the exact error-template sentence (server `step_label` + `last_error` truncated to 200 chars). Any non-terminal row exposes a cancel button opening a Radix Dialog with the UI-SPEC's verbatim cost-non-refund disclosure. Grep-verified zero `spinner`/`Spinner` occurrences (ING-06).
- `SourcesList.tsx` (new file, not in the plan's original file list — see Deviations) + `sources/page.tsx`: Server Component reads `raw_sources` via RLS (`raw_sources_select_member`), excludes the `content` column, caps at 50 rows, passes the result into the client wrapper. Client wrapper renders `Dropzone` above a per-source list, each row rendering its own `JobStepper`; `Dropzone.onIngested` triggers a single targeted Supabase row read (not a full list refetch) to prepend the new source. Empty state renders the exact UI-SPEC copy.
- All 3 tasks' `<verify>` commands pass: `pnpm exec vitest run tests/Dropzone.test.tsx` (7/7), `pnpm exec vitest run tests/JobStepper.test.tsx` (3/3), `pnpm exec tsc --noEmit` (clean). Full suite re-verified at 49/49 passing and `pnpm exec next build` succeeds with `/w/[workspaceId]/sources` registered as a dynamic route.

## Task Commits

1. **Task 1: Dropzone.tsx** - `772b38f` (feat)
2. **Task 2: JobStepper.tsx** - `bf1697b` (feat)
3. **Task 3: sources/page.tsx + SourcesList.tsx** - `f51db8a` (feat)

**Plan metadata:** _(this commit, follows below)_

## Files Created/Modified

- `apps/dashboard/components/Dropzone.tsx` - 3-tab (file/URL/text) source ingest component
- `apps/dashboard/tests/Dropzone.test.tsx` - Vitest + Testing Library, 7 tests
- `apps/dashboard/components/JobStepper.tsx` - real 5-stage job-chain progress, retry/cancel
- `apps/dashboard/tests/JobStepper.test.tsx` - Vitest + Testing Library, 3 tests
- `apps/dashboard/components/SourcesList.tsx` - client wrapper (Dropzone + per-source JobStepper), not in original plan file list
- `apps/dashboard/app/w/[workspaceId]/sources/page.tsx` - `/sources` route, Server Component RLS read

## Decisions Made

- JobStepper's 5 header captions are a separate hardcoded D-05-verbatim caption set, not a duplicate of `jobs.py`'s `STEP_LABELS` — `STEP_LABELS`/`step_label` is only consumed for the dead-row error template, per the plan's own instruction not to re-derive that server-owned map client-side.
- `SourcesList.tsx`'s `onIngested` does a single targeted Supabase row read instead of a full 50-row refetch, since `Dropzone`'s fixed 2-arg callback (`jobId`, `rawSourceId`) carries no title/type/date, and `sources.py` guarantees the row exists (committed before the 202 response) by the time `apiFetch` resolves.
- Renamed the URL tab's field label from bare "URL" to "URL 주소" to resolve a `getByLabelText` ambiguity against Radix's `aria-labelledby`-on-tabpanel (which points at the tab trigger, whose own visible text is also "URL").

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added `SourcesList.tsx` (not in the plan's file list)**
- **Found during:** Task 3 implementation
- **Issue:** The plan's own `<action>` requires `sources/page.tsx` to be a Server Component fetching the initial list, but `Dropzone.onIngested` prepending new sources to local state requires client-side state, which a Server Component cannot hold. This is the same structural gap `06-03-SUMMARY.md` documented for `SettingsMembersPanel.tsx`.
- **Fix:** Added a thin `"use client"` wrapper (`SourcesList.tsx`) holding the `sources` array state, rendered by the Server Component `page.tsx`.
- **Files modified:** `apps/dashboard/components/SourcesList.tsx` (new), `apps/dashboard/app/w/[workspaceId]/sources/page.tsx`
- **Verification:** `tsc --noEmit` clean; `next build` succeeds with the route registered; Vitest suite unaffected (49/49).
- **Committed in:** `f51db8a`

**2. [Rule 1 - Bug] Radix Tabs did not switch under `fireEvent.click` in jsdom tests**
- **Found during:** Task 1's own Dropzone.test.tsx authoring
- **Issue:** Radix Tabs' default `activationMode="automatic"` switches the active tab on focus, not on a bare synthetic click; `fireEvent.click` does not simulate focus, so the URL/text tab panels never mounted and `getByLabelText` failed against elements that don't exist yet (or, after a related fix, against an ambiguous match).
- **Fix:** Switched tab-switching interactions in the test file to `@testing-library/user-event`'s `user.click`, which does simulate the focus step.
- **Files modified:** `apps/dashboard/tests/Dropzone.test.tsx`
- **Verification:** All 7 Dropzone tests pass.
- **Committed in:** `772b38f`

**3. [Rule 1 - Bug] `getByLabelText("URL")` ambiguity between the form field and the tab trigger**
- **Found during:** Task 1's own Dropzone.test.tsx authoring (after fixing #2 above)
- **Issue:** Once tab switching worked, `getByLabelText("URL")` matched two elements: the real `<input>` (via its own `<label>URL</label>`) and the URL tabpanel `<div>` (via `aria-labelledby` pointing at the trigger button, whose visible text is also "URL").
- **Fix:** Renamed the form field's label to "URL 주소" (component change) and updated the test queries to match.
- **Files modified:** `apps/dashboard/components/Dropzone.tsx`, `apps/dashboard/tests/Dropzone.test.tsx`
- **Verification:** All 7 Dropzone tests pass.
- **Committed in:** `772b38f`

---

**Total deviations:** 3 auto-fixed (1 blocking file addition, 2 test-authoring bugs — no production-code bug beyond the label rename)
**Impact on plan:** All three were necessary for the plan's own `<done>`/`<acceptance_criteria>` to be genuinely satisfiable (a Server-Component page that can still hold client refresh state, and tests that actually exercise the Radix Tabs interaction they claim to test). No scope creep beyond this plan's stated UI-03 boundary.

## Issues Encountered

- `rtk` (the project's token-optimized command proxy) silently swallowed `screen.debug()`/console output during initial debugging, making the Radix-Tabs-doesn't-switch failure hard to diagnose via normal `console.log`/`screen.debug` — worked around by writing DOM snapshots to a file with `fs.writeFileSync` instead, and by using `rtk proxy <cmd>` to bypass the filtering for subsequent test runs in this session.
- `pnpm --filter @nexuswiki/dashboard ...` from the repo root fails (`ERR_PNPM_NO_PKG_MANIFEST`) since `apps/dashboard` is a standalone pnpm project (own lockfile, no root workspace file per `01-CONTEXT.md` D-09/D-10) — all commands in this plan were run with `cd apps/dashboard && pnpm exec ...` instead of the plan's literal `pnpm --filter @nexuswiki/dashboard exec ...` invocation. Same underlying package layout as every prior Phase 6 plan; noting here since this plan's own `<verify>` blocks are written with the `--filter` form.

## User Setup Required

None — no external service configuration required. All verification in this session used mocked `apiFetch`/Supabase clients (Vitest) plus static build/typecheck; no live Supabase/API credentials were needed.

## Next Phase Readiness

- UI-03 is code-complete and unit-verified: 3-tab ingest with correct raw-bytes/error-copy behavior, a real 5-stage job stepper with retry/cancel, and a wired `/sources` route with the documented empty state.
- **Not yet live-verified (D6 above):** no session process had `apps/api`, the worker, or `next dev` running (only the local Supabase Docker stack was up) — a future session should run the full click-through (upload a file, watch parse→compile→link_sync→embed progress, trigger a dedup 409, trigger a retry) against the real local stack before this is considered fully proven, matching the same-class gaps `06-01`/`06-02`/`06-03` already documented for RSC/middleware/RLS live behavior.
- **D7 backstop (source-list loading skeleton):** intentionally not implemented as a literal loading-state branch because Task 3's own SSR-first design means the outer list never has a client-side loading phase; flagged for human judgment rather than silently marked covered.
- `Dropzone.tsx`/`JobStepper.tsx` are self-contained and reusable — no other Phase 6 plan currently depends on them, but `06-06`(Ask UI) or a future citation-linking feature could reasonably link back to a specific source's `JobStepper` state.

---
*Phase: 06-dashboard*
*Completed: 2026-08-12*

## Self-Check: PASSED

All 6 created files confirmed on disk. All 3 task commit hashes (`772b38f`, `bf1697b`, `f51db8a`) confirmed in `git log`. `pnpm exec vitest run` (49/49 passing), `pnpm exec tsc --noEmit` (clean), and `pnpm exec next build` (succeeds, route registered) all re-confirmed before writing this summary.

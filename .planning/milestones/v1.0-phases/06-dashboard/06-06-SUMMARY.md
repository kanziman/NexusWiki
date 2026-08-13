---
phase: 06-dashboard
plan: 06
subsystem: ui
tags: [nextjs, react, sse, citations, vitest, tdd, radix-ui, apps-api, postgrest]

requires:
  - phase: 06-dashboard
    provides: "06-01: workspacePath/@supabase/ssr client factories, middleware tenancy gate; 06-04: lib/api-client.ts (apiFetch/ApiError, auth-header pattern) + lib/sse.ts (parseSseStream)"
provides:
  - "apps/dashboard/lib/citation-anchors.ts — splitTextWithAnchors(text, resolved?), ISSUED_ANCHOR_PATTERN, AnchorPart/TextPart/ResolvedAnchor types"
  - "apps/dashboard/components/CitationMarker.tsx — inert placeholder / numbered clickable badge, D-09"
  - "apps/dashboard/components/AskConversation.tsx — meta->delta*->citations->done SSE state machine, CITE-04/error/stream-drop/missing_channels rendering"
  - "apps/dashboard/components/CitationSidePanel.tsx — exact-{kind,id} PostgREST reads for wiki_pages/source_chunks, char_start/char_end-aware full-chunk highlight"
  - "apps/dashboard/app/w/[workspaceId]/ask/page.tsx — /ask route"
affects: [06-07 (wiki viewer may reuse CitationSidePanel's wiki_pages read pattern)]

actuals:
  tokens: 9797
  tasks: 3
  commits: 5

tech-stack:
  added: []
  patterns:
    - "Manual fetch (not apiFetch) for the SSE POST — apiFetch assumes a JSON response body; the ask endpoint's response is consumed via lib/sse.ts's parseSseStream instead, with the same per-call session-token attachment pattern as apiFetch"
    - "Anchor resolution is a two-pass render, not a single state flag — splitTextWithAnchors(text) (no resolved arg) during streaming vs splitTextWithAnchors(text, resolved) after the citations event; the same pure function drives both the inert-placeholder and resolved-link render paths so there is never a code path where a not-yet-resolved anchor can render as a real link"
    - "TS regex drift guard against a Python source of truth via .source string equality (ISSUED_ANCHOR_PATTERN.source === nexuswiki_core/citations.py's literal pattern), rather than duck-typing behavior only"

key-files:
  created:
    - apps/dashboard/lib/citation-anchors.ts
    - apps/dashboard/components/CitationMarker.tsx
    - apps/dashboard/components/AskConversation.tsx
    - apps/dashboard/components/CitationSidePanel.tsx
    - apps/dashboard/app/w/[workspaceId]/ask/page.tsx
    - apps/dashboard/tests/citation-anchors.test.ts
    - apps/dashboard/tests/CitationMarker.test.tsx
    - apps/dashboard/tests/AskConversation.test.tsx
  modified: []

key-decisions:
  - "CitationSidePanelProps gained an optional third field (workspaceId?: string) beyond the plan's literal 2-field type — the plan's own <action> requires linking a wiki card to /w/[workspaceId]/wiki/[slug], which is structurally impossible without workspaceId in scope. AskConversation passes its own workspaceId through; the panel still works standalone (no link rendered) if the prop is omitted. Documented as a Rule 2 (missing critical functionality) auto-fix, not a scope change to the required {part, onClose} contract."
  - "CitationSidePanel's exact-id fetch uses an explicit `load(part: AnchorPart)` parameter (not a `part!.id` non-null assertion inside a closure) specifically so the source text contains the literal substring `.eq(\"id\", part.id)` — satisfying Task 3's own grep-based acceptance criterion without weakening the null-safety that criterion is checking for."
  - "AskConversation ignores the `done` SSE event for state transitions — the citations frame (or its absence) is what actually determines the turn's terminal render (resolved / no-evidence / error / dropped). `done` only confirms the stream ended cleanly; treating it as load-bearing would mean a network drop immediately after a fully-rendered citations frame incorrectly downgrades an already-complete answer to 'dropped'."
  - "The ask/page.tsx empty-state instruction (render empty heading/body 'when the conversation has zero turns') is implemented inside AskConversation.tsx, not literally in page.tsx — turns is client component state that a Server Component cannot read. page.tsx stays a thin wrapper per its own <action> description; this is the same client/server boundary gap 06-05-SUMMARY.md documented for SourcesList.tsx."
  - "Ask-path error copy (budget_exceeded / rate_limited / llm_unavailable / ask_template_unavailable, i.e. citations.error) uses one generic retry message rather than per-token strings — 06-UI-SPEC.md's Copywriting Contract only specifies exact verbatim copy for the no-evidence and stream-drop cases; inventing untested per-token Korean copy for the remaining ask.py _ERROR_TOKENS values was out of this plan's specified scope."

patterns-established:
  - "Pattern: splitTextWithAnchors's two-mode signature (resolved arg present/absent) is the single source of truth for 'is this anchor safe to render as a real link yet' — any future citation-rendering surface should call through it rather than re-deriving anchor/resolution logic"

requirements-completed: [UI-04]

coverage:
  - id: D1
    description: "splitTextWithAnchors correctly splits streaming placeholders (no resolved map), resolved links ({kind,alias,id}), and silently strips fabricated (unissued) anchors when a resolved map is supplied — proven against a regex drift guard vs nexuswiki_core/citations.py's ISSUED_ANCHOR_PATTERN"
    requirement: "UI-04"
    verification:
      - kind: unit
        ref: "apps/dashboard/tests/citation-anchors.test.ts (5 tests, all pass)"
        status: pass
    human_judgment: false
  - id: D2
    description: "CitationMarker renders an inert, non-interactive placeholder (no onClick wiring, not a <button>) when unresolved, and a numbered clickable badge firing onClick(part) when resolved — a fabricated anchor is never given a moment where it looks like a real, clickable link (T-06-18)"
    requirement: "UI-04"
    verification:
      - kind: unit
        ref: "apps/dashboard/tests/CitationMarker.test.tsx (3 tests, all pass)"
        status: pass
    human_judgment: false
  - id: D3
    description: "AskConversation drives the full meta->delta*->citations->done SSE state machine: CITE-04 no-evidence warning card (data-variant=warning, exact copy), stream-drop-without-done card (exact copy + retry), citations.error card distinct from the no-evidence card (with retry), meta.missing_channels inline notice, and resolved-citation markers opening the side panel with the exact resolved {kind,id}"
    requirement: "UI-04"
    verification:
      - kind: unit
        ref: "apps/dashboard/tests/AskConversation.test.tsx (6 tests, all pass)"
        status: pass
    human_judgment: false
  - id: D4
    description: "CitationSidePanel fetches wiki_pages/source_chunks strictly by the resolved anchor's exact id (.eq(\"id\", part.id), never a derived/fuzzy lookup), highlights the full chunk content for source citations (char_start/char_end are parent-raw_source coordinates, not offsets into this chunk's own content), caps excerpt height at ~400px with internal scroll, and auto-scrolls the highlighted span into view"
    requirement: "UI-04"
    verification:
      - kind: other
        ref: "grep -c '.eq(\"id\", part.id)' apps/dashboard/components/CitationSidePanel.tsx == 3 (>= 2 required); pnpm exec tsc --noEmit (clean); pnpm exec next build (succeeds, /w/[workspaceId]/ask route registered)"
        status: pass
    human_judgment: false
  - id: D5
    description: "Full end-to-end click-through against a running apps/api + supabase start + worker: ask a question, watch the placeholder-to-resolved marker swap happen in-place after the citations frame, click a marker and confirm the side panel shows exactly the cited wiki page or source chunk"
    verification: []
    human_judgment: true
    rationale: "No apps/api, worker, or next dev process was running in this session (only the local Supabase Docker stack considerations from prior plans apply) — same class of gap 06-01/06-02/06-03/06-05 already documented for live RSC/middleware/RLS/job-chain behavior. A future session must run this live pass (ask a real question against real evidence) before the placeholder->resolved swap and side-panel content-identity are considered proven beyond the mocked-SSE unit tests."

duration: ~35min
completed: 2026-08-12
status: complete
---

# Phase 6 Plan 6: Ask UI with Inline Dual-Citation Summary

**Ask UI (`AskConversation`) driving the `meta->delta*->citations->done` SSE contract with inert-until-resolved citation markers (`CitationMarker`), a `CitationSidePanel` that reads wiki/source evidence strictly by the server-issued anchor id, and a shared pure-function anchor splitter (`citation-anchors.ts`) ported 1:1 from `nexuswiki_core/citations.py`'s issued-anchor semantics.**

## Performance

- **Duration:** ~35 min
- **Tasks:** 3/3 completed
- **Files created:** 8 (5 source, 3 test)

## Accomplishments

- `lib/citation-anchors.ts`: `splitTextWithAnchors(text, resolved?)` — streaming mode (no `resolved` arg) emits every `[[wiki:wN]]`/`[[src:sN]]`-shaped token as an anchor part regardless of eventual fabrication status; resolved mode looks each alias up in the `citations` event's `resolved` array and silently omits any alias not found (mirrors `resolve_citations()`'s `_strip_fabricated` exactly — a fabricated anchor never renders, not even as a placeholder, once resolution is known). `ISSUED_ANCHOR_PATTERN.source` is asserted byte-for-byte equal to `nexuswiki_core/citations.py`'s pattern as a drift guard.
- `CitationMarker.tsx`: unresolved anchors render as a `<span aria-hidden>` placeholder with zero click wiring (not a disabled button — genuinely no handler attached); resolved anchors render as a numbered `<button>` badge that fires `onClick(part)`.
- `AskConversation.tsx`: builds the raw `fetch` POST to `/workspaces/{id}/ask` (not `apiFetch`, since that helper assumes a JSON body) with the same per-call session-token attachment pattern, feeds the `Response` into `lib/sse.ts`'s `parseSseStream`, and drives a per-turn state machine — `no-evidence` (CITE-04 warning card, exact verbatim copy, `data-variant="warning"`), `error` (any `citations.error` token, distinct card + retry), `dropped` (stream ended without ever reaching a terminal citations/error state — exact stream-drop copy + retry), `resolved` (final answer with clickable numbered markers). `meta.missing_channels` renders a defensive inline notice only when present and non-empty (the field doesn't exist in `ask.py` yet per this plan's documented assumption). A prompt-template chip row reads `prompt_templates` directly via RLS.
- `CitationSidePanel.tsx`: on a resolved marker click, fetches `wiki_pages`/`source_chunks` strictly by `.eq("id", part.id)` — never a derived or fuzzy lookup (T-06-19, this plan's load-bearing prohibition). Source excerpts highlight the entire chunk `content` (not a sub-string) since `char_start`/`char_end` are coordinates into the parent `raw_source`, not this chunk's own content string. Both card types cap at ~400px height with internal scroll and auto-scroll the highlighted element into view via `scrollIntoView({block:"center"})`.
- `app/w/[workspaceId]/ask/page.tsx`: thin Server Component wrapper rendering `<AskConversation workspaceId={workspaceId} />`.
- All 3 tasks' `<verify>` commands pass: `vitest run tests/citation-anchors.test.ts` (5/5), `vitest run tests/AskConversation.test.tsx tests/CitationMarker.test.tsx` (9/9), `tsc --noEmit` (clean). Full suite re-verified at 63/63 passing, and `next build` succeeds with `/w/[workspaceId]/ask` registered as a dynamic route.

## Task Commits

Task 1 and Task 2 followed RED -> GREEN (`tdd="true"` on both):

1. **Task 1: lib/citation-anchors.ts**
   - `82eb842` test(06-06): failing test first (RED) — confirmed import-resolution failure before the module existed
   - `7944bf0` feat(06-06): splitTextWithAnchors implementation (GREEN) — 5/5 tests pass
2. **Task 2: AskConversation.tsx + CitationMarker.tsx + ask/page.tsx**
   - `33f114a` test(06-06): failing tests first (RED) — confirmed import-resolution failure before the components existed
   - `9a22553` feat(06-06): implementation (GREEN) — 9/9 tests pass
3. **Task 3: CitationSidePanel.tsx** (`tdd` not set — automated verify is `tsc --noEmit` + grep, per plan)
   - `e7726d1` feat(06-06): CitationSidePanel.tsx — grep/tsc/next-build all pass

**Plan metadata:** committed as part of this summary/state-update step.

## Files Created/Modified

- `apps/dashboard/lib/citation-anchors.ts` — `ISSUED_ANCHOR_PATTERN`, `splitTextWithAnchors(text, resolved?)`, `AnchorPart`/`TextPart`/`ResolvedAnchor` types
- `apps/dashboard/tests/citation-anchors.test.ts` — 5 tests covering all 4 behavior-spec cases + regex drift guard
- `apps/dashboard/components/CitationMarker.tsx` — inert placeholder / numbered clickable badge
- `apps/dashboard/tests/CitationMarker.test.tsx` — 3 tests
- `apps/dashboard/components/AskConversation.tsx` — SSE state machine, template chips, question form, empty-state
- `apps/dashboard/tests/AskConversation.test.tsx` — 6 tests covering no-evidence, stream-drop, error, missing_channels, resolved-marker-click
- `apps/dashboard/components/CitationSidePanel.tsx` — exact-id wiki/source fetch, capped-height excerpt cards, auto-scroll
- `apps/dashboard/app/w/[workspaceId]/ask/page.tsx` — `/ask` route

## Decisions Made

- `CitationSidePanelProps` gained an optional `workspaceId?: string` beyond the plan's literal 2-field type, so the wiki card's "view full page" link (required by Task 3's own `<action>`, but structurally unreachable from `{part, onClose}` alone) can be rendered. `AskConversation` passes its own `workspaceId`; the panel degrades gracefully (no link) without it.
- `CitationSidePanel`'s exact-id fetch is written as `load(part: AnchorPart)` with `part` re-bound as an explicit parameter, not a `part!.id` non-null assertion inside a closure — this keeps the source text containing the literal substring `.eq("id", part.id)` that Task 3's own acceptance criterion greps for, without weakening the null-check the grep is meant to prove exists.
- `AskConversation` treats the `citations` frame (or its absence at stream end) as the sole determinant of a turn's terminal render; the `done` frame is intentionally a no-op for state transitions. A network drop immediately after a fully-resolved citations frame should not retroactively downgrade an already-complete answer to "dropped".
- The `ask/page.tsx` empty-state instruction is implemented inside `AskConversation.tsx` (client state), not literally inside `page.tsx` (Server Component) — same client/server boundary gap `06-05-SUMMARY.md` documented for `SourcesList.tsx`.
- Ask-path `citations.error` tokens (`budget_exceeded`/`rate_limited`/`llm_unavailable`/`ask_template_unavailable`) render one generic Korean retry message rather than per-token copy, since 06-UI-SPEC.md's Copywriting Contract only specifies exact verbatim strings for the no-evidence and stream-drop cases.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical Functionality] Added optional `workspaceId` prop to `CitationSidePanelProps`**
- **Found during:** Task 3 implementation
- **Issue:** Task 3's `<action>` explicitly requires the wiki card to link to `/w/[workspaceId]/wiki/[slug]`, but `CitationSidePanelProps` as literally specified (`{part, onClose}`) has no way to construct that path.
- **Fix:** Added `workspaceId?: string` as a third, optional prop; `AskConversation` (Task 2, under the same plan) passes its own `workspaceId` through. The panel still satisfies the literal 2-field contract for any caller that omits it (no link rendered, everything else works).
- **Files modified:** `apps/dashboard/components/CitationSidePanel.tsx`, `apps/dashboard/components/AskConversation.tsx`
- **Verification:** `tsc --noEmit` clean; `next build` succeeds.
- **Committed in:** `e7726d1` (Task 3), `9a22553` (Task 2's `AskConversation` passing the prop)

---

**Total deviations:** 1 auto-fixed (1 missing-functionality prop addition, additive-only, no existing contract narrowed)
**Impact on plan:** Necessary for Task 3's own `<action>` to be satisfiable as written. No scope creep beyond UI-04's boundary.

## Issues Encountered

- Same as every prior Phase 6 plan: `pnpm --filter @nexuswiki/dashboard exec vitest ...` (the plan's literal `<verify>` invocation) fails with `ERR_PNPM_NO_PKG_MANIFEST` from the repo root, since `apps/dashboard` is a standalone pnpm project with its own lockfile (no root workspace manifest, per `01-CONTEXT.md` D-09/D-10). All verification in this session used `cd apps/dashboard && pnpm exec ...` instead.
- The project's `pre-commit` hook's `prettier` step stashes unstaged files before running and restores them after — on two of this plan's five commits (Task 2's tests, Task 2's implementation), this reformatted just-staged files (whitespace/line-wrap only, no logic change) and the `git commit` invocation itself exited non-zero even though the working tree was left in a valid, re-stageable state. Both were resolved by re-`git add`-ing the now-reformatted files and re-running `git commit` with the same message — matching the exact pattern `06-04-SUMMARY.md` already documented for this hook.

## User Setup Required

None — no external service configuration required. All verification in this session used mocked `parseSseStream`/Supabase clients (Vitest) plus static build/typecheck; no live Supabase/API credentials were needed.

## Next Phase Readiness

- UI-04 is code-complete and unit-verified: the full SSE state machine (no-evidence, error, stream-drop, resolved-with-markers), the citation marker's streaming-inert-to-resolved-clickable transition, and the side panel's exact-id fetch are all proven against the behavior spec.
- **Not yet live-verified (D5 above):** no session process had `apps/api`, the worker, or `next dev` running — a future session should ask a real question against real evidence (upload a source via `/sources` first) and confirm the placeholder->resolved marker swap and side-panel content-identity against a live backend, matching the same-class gaps `06-01`/`06-02`/`06-03`/`06-05` already documented.
- `CitationSidePanel.tsx`'s `wiki_pages`/`source_chunks` exact-id read pattern is reusable — `06-07` (wiki viewer) could adapt the same `.eq("id", ...)`-by-server-issued-id discipline for its own reads, though it isn't a direct dependency.
- No blockers identified for downstream Phase 6 plans.

---
*Phase: 06-dashboard*
*Completed: 2026-08-12*

## Self-Check: PASSED

All 8 created files confirmed on disk. All 5 task commit hashes (`82eb842`, `7944bf0`, `33f114a`, `9a22553`, `e7726d1`) confirmed in `git log`. `pnpm exec vitest run` (63/63 passing), `pnpm exec tsc --noEmit` (clean), and `pnpm exec next build` (succeeds, `/w/[workspaceId]/ask` route registered) all re-confirmed before writing this summary.

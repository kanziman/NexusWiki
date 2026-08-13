---
phase: 06-dashboard
plan: 02
subsystem: ui
tags: [nextjs, radix-ui, react-transition, workspace-switcher, navigation, vitest]

requires:
  - phase: 06-dashboard
    provides: "06-01: @supabase/ssr client/server factories, middleware.ts tenancy gate, /w/[workspaceId] RLS-scoped single-row workspace read, Tailwind 4 @theme tokens, workspacePath() helper"
provides:
  - "WorkspaceSwitcher.tsx — Radix dropdown-menu workspace switcher consuming workspacePath(), active-item indication, scroll/tooltip/loading backstops"
  - "NavShell.tsx — the workspace shell's real navigation surface (switcher + 5 route links), replacing 06-01's bare header"
  - "app/w/[workspaceId]/layout.tsx now issues a second RLS-scoped direct read (full member workspace list, no .eq filter) alongside the existing single-row lookup"
affects: [06-03, 06-04, 06-05, 06-06, 06-07, 06-08]

actuals:
  tokens: 3378
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "React useTransition() wraps router.push() in WorkspaceSwitcher to derive a per-item pending/loading state (Next.js App Router idiom for route-transition loading UI) instead of a separate isLoading flag"
    - "Radix dropdown-menu Item wrapped in a Radix tooltip Root/Trigger/Content pair per row, for the long-text truncation backstop"
    - "vitest.setup.ts now polyfills Element.prototype.{hasPointerCapture,setPointerCapture,releasePointerCapture,scrollIntoView} and window.ResizeObserver globally — required by every Radix UI primitive under jsdom, shared by all future Phase 6 component tests"

key-files:
  created:
    - apps/dashboard/components/WorkspaceSwitcher.tsx
    - apps/dashboard/components/NavShell.tsx
    - apps/dashboard/tests/WorkspaceSwitcher.test.tsx
  modified:
    - apps/dashboard/app/w/[workspaceId]/layout.tsx
    - apps/dashboard/vitest.setup.ts

key-decisions:
  - "Chevron aria-label lives on a role=\"img\" span nested inside the single Radix Trigger <button>, not on a second real <button> — a native <button> cannot nest another interactive <button>, and Radix's Trigger asChild pattern only clones onto one element"
  - "Pending/loading state (backstop) implemented via React's useTransition() wrapping router.push(), not a manual isLoading boolean — this is the idiomatic Next.js App Router signal for 'a route transition triggered by this action is in flight', and it resolves automatically when the new route's RSC payload lands, with no separate cleanup path to get wrong"
  - "jsdom Pointer Capture / scrollIntoView / ResizeObserver polyfills added globally in vitest.setup.ts rather than per-test-file — every Radix UI primitive listed in the UI-SPEC (dropdown-menu, tooltip, tabs, dialog, select) needs the same polyfills under jsdom, so every later Phase 6 plan's component tests inherit this for free"

patterns-established:
  - "Radix dropdown-menu Item + Radix tooltip Root/Trigger/Content nesting for any future truncated-label-in-a-list UI (source rows, member rows will likely reuse this)"

requirements-completed: [UI-01]

coverage:
  - id: D1
    description: "WorkspaceSwitcher renders the current workspace's name in its trigger, marks the matching dropdown item data-active=\"true\" (and only that one), and the chevron control carries aria-label=\"워크스페이스 전환\""
    requirement: UI-01
    verification:
      - kind: unit
        ref: "apps/dashboard/tests/WorkspaceSwitcher.test.tsx (4 tests: aria-label present, only current item data-active, selecting a non-current item calls router.push, selecting the current item is a no-op)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Selecting a non-current workspace in the switcher calls router.push(workspacePath(id)) with the helper's exact return value, not an inlined path string"
    requirement: UI-01
    verification:
      - kind: unit
        ref: "apps/dashboard/tests/WorkspaceSwitcher.test.tsx — \"활성이 아닌 워크스페이스를 선택하면 workspacePath()로 이동한다\""
        status: pass
    human_judgment: false
  - id: D3
    description: "NavShell renders the switcher plus 5 working links (소스/질문하기/위키/그래프/설정) built from workspacePath(currentWorkspaceId); layout.tsx adds exactly one additional RLS-scoped workspaces read (no .eq filter) beyond the existing single-row lookup, and replaces 06-01's bare header with NavShell"
    requirement: UI-01
    verification:
      - kind: other
        ref: "tsc --noEmit clean; next build succeeds (4 routes, 0 errors/warnings); grep confirms two .from(\"workspaces\") call sites in layout.tsx, one .single() and one .order(\"name\")"
        status: pass
    human_judgment: false
  - id: D4
    description: "End-to-end: signing in lands the caller on their own workspace, all 5 nav links resolve under the correct workspace id, opening the switcher lists every workspace the caller belongs to with the active one marked, and selecting a different workspace performs a real client-side navigation to /w/[otherId] after which every nav link (e.g. 소스) recomputes its href against the new workspace id"
    requirement: UI-01
    verification:
      - kind: manual_procedural
        ref: "Throwaway test account (admin API) + two workspaces (inserted directly via docker exec psql, since service_role lacks table-level INSERT grants per 0007's least-privilege matrix) + a plain Playwright script (not a gstack skill) driving the local next dev server against the running supabase start stack: login -> /w/{ws1} -> all 5 links present + chevron aria-label present -> open switcher -> both workspace names listed, ws1 item data-active -> click ws2 -> navigated to /w/{ws2} -> 소스 link href recomputed to /w/{ws2}/sources. Both the account and both workspaces were deleted immediately after (verified 0 rows/0 users remaining)."
        status: pass
    human_judgment: true
    rationale: "Requires a live Supabase stack, a real auth session, RLS enforcement, and an actual browser render/click sequence (Radix portal-rendered dropdown content, client-side router.push navigation) — not reproducible inside the project's Vitest/jsdom harness, same limitation 06-01 documented for its own manual_procedural checks."

duration: ~35min
completed: 2026-08-12
status: complete
---

# Phase 6 Plan 2: Workspace Switcher and Navigation Shell Summary

**Radix dropdown-menu workspace switcher wired to `workspacePath()` navigation, plus a `NavShell` replacing 06-01's bare header with real links to all five remaining Phase 6 surfaces — UI-01 is now fully satisfied end to end.**

## Performance

- **Duration:** ~35 min active implementation across both tasks, including a full local-stack Playwright verification pass
- **Tasks:** 2/2 completed
- **Files modified:** 5 (3 created, 2 modified)

## Accomplishments

- Built `WorkspaceSwitcher.tsx`: a Radix `dropdown-menu` over the caller's own RLS-scoped workspace list, with the active workspace marked `data-active="true"` and colored `text-primary`, a 44x44px chevron control carrying `aria-label="워크스페이스 전환"` (WCAG 2.5.5), a scrollable `max-h-64` dropdown past ~8 workspaces, per-row Radix tooltips exposing the full name for CSS-truncated long workspace names, and a `useTransition()`-driven pending state that disables + spinners the selected item while the target route's RSC payload is still loading.
- Built `NavShell.tsx`: renders the switcher plus five `next/link` links (소스/질문하기/위키/그래프/설정) built from `workspacePath(currentWorkspaceId)`, with `usePathname()`-driven active-route styling — replacing the bare `<h1>{workspace.name}</h1>` header the 06-01 tracer left in place.
- Extended `app/w/[workspaceId]/layout.tsx` with a second direct PostgREST read (`workspaces` table, no `.eq` filter — RLS `workspaces_select_member` already scopes it to the caller's own memberships) supplying the switcher's full list, while leaving the existing single-row `.eq(id).single()` lookup (which decides "does this workspace exist / am I a member" and drives the D-12 no-enumeration redirect) untouched.
- Added global jsdom polyfills (`Element.prototype.hasPointerCapture`/`setPointerCapture`/`releasePointerCapture`/`scrollIntoView`, `window.ResizeObserver`) to `vitest.setup.ts` — every Radix UI primitive the UI-SPEC names (dropdown-menu, tooltip, tabs, dialog, select) calls these under the hood, and jsdom 30 implements none of them; without this fix every Radix-based component test in Phase 6 (not just this plan's) would fail with "not a function" errors.
- Verified the entire flow end-to-end against the real local Supabase stack with a throwaway account + two throwaway workspaces and a plain Playwright script (not a gstack-branded skill, per project constraint): login → lands on own workspace → all 5 links + chevron aria-label present → switcher lists both workspaces with the active one marked → selecting the other workspace performs a real navigation to `/w/[otherId]` → the 소스 link's `href` recomputes against the new workspace id. Both the account and both workspaces were deleted immediately after.

## Task Commits

Each task was committed individually:

1. **Task 1: WorkspaceSwitcher.tsx — Radix dropdown over a direct-read workspace list** - `e0ca3f6` (feat)
2. **Task 2: NavShell.tsx — wire switcher + route links into the workspace layout** - `c9d8b65` (feat)

**Plan metadata:** _(this commit, follows below)_

## Files Created/Modified

- `apps/dashboard/components/WorkspaceSwitcher.tsx` - `WorkspaceSwitcher` component, `WorkspaceSwitcherProps` type
- `apps/dashboard/components/NavShell.tsx` - `NavShell` component, `NavShellProps` type
- `apps/dashboard/tests/WorkspaceSwitcher.test.tsx` - Vitest + Testing Library, 4 tests
- `apps/dashboard/app/w/[workspaceId]/layout.tsx` - Added second RLS-scoped `workspaces` read; replaced bare header with `<NavShell>`
- `apps/dashboard/vitest.setup.ts` - Radix-required jsdom polyfills (pointer capture, scrollIntoView, ResizeObserver)

## Decisions Made

- Chevron `aria-label` placed on a `role="img"` span nested inside the single Radix `Trigger` `<button>`, rather than a second real `<button>` — HTML forbids nesting interactive `<button>` elements, and Radix's `asChild` pattern only clones props onto one child element.
- Implemented the workspace-switcher loading backstop with React's `useTransition()` wrapping `router.push()`, instead of a manually-managed `isLoading` boolean — this is the idiomatic Next.js App Router signal for "a route transition triggered by this action is in flight" and resolves itself when the new route's RSC payload lands, with no separate cleanup path to get wrong.
- Added the Radix-required jsdom polyfills globally in `vitest.setup.ts` rather than scoped to this one test file, since every later Phase 6 plan's Radix-based components (tabs, dialog, select — per 06-UI-SPEC.md Design System table) will hit the identical jsdom gaps.

## Deviations from Plan

None — plan executed as written. The jsdom polyfill addition to `vitest.setup.ts` is infrastructure the plan's own acceptance criterion ("covered by a passing Vitest suite") required to be satisfiable at all under Radix UI, not a scope change; it's the same category of "necessary for the plan's own `<done>` criterion to be achievable" as 06-01's `page.tsx` addition, so it's called out here rather than silently folded into Task 1.

## Issues Encountered

- `pnpm --filter @nexuswiki/dashboard <cmd>` from the repo root fails with `ERR_PNPM_NO_PKG_MANIFEST` (no root `package.json`/`pnpm-workspace.yaml` — `apps/dashboard` is intentionally its own isolated pnpm workspace per `01-CONTEXT.md` D-09/D-10). Ran all `pnpm exec`/`node_modules/.bin/*` commands from inside `apps/dashboard/` instead — no functional impact, just a filter-flag mismatch with this project's deliberate non-monorepo pnpm layout.
- The pre-commit `prettier` hook reformatted both new files on the first commit attempt for each task (whitespace/line-wrap only), which aborts the commit per pre-commit's normal behavior. Re-staged the reformatted files and re-ran tests/tsc before re-committing both times — no code semantics changed, confirmed via re-running the full test suite and `tsc --noEmit` after each reformat.
- `service_role` cannot `INSERT` directly into `public.workspaces` via PostgREST (`42501` — matches the documented least-privilege matrix from `0007` §8: table grants are intentionally not given to `service_role`, only `SECURITY DEFINER`/`SECURITY INVOKER` function paths and direct `psql` are). Used `docker exec -it supabase_db_NexusWiki psql` for the throwaway verification workspaces instead, per the project's own documented convention (`CLAUDE.md` "로컬 `psql` 없음" row).
- Playwright's installed version (1.59.1, from a sibling project's `node_modules`) expected a Chromium build (`chromium_headless_shell-1217`) not present in the local `~/Library/Caches/ms-playwright` cache (which had 1208/1223/1228). Launched with an explicit `executablePath` pointing at the cached `chromium-1228` "Google Chrome for Testing" binary instead of downloading a new browser — no new download, reused what was already on disk.

## User Setup Required

None.

## Next Phase Readiness

- UI-01 is now fully satisfied end to end: login → tenancy-gated `/w/[workspaceId]` → workspace switching by URL → navigation to every other Phase 6 surface (소스/질문하기/위키/그래프/설정) all work, verified live against the local Supabase stack.
- `WorkspaceSwitcher.tsx` and `NavShell.tsx` are ready for later plans (06-03 dropzone lives under `/sources`, 06-04 under `/ask`, 06-05 wiki viewer under `/wiki`, 06-06 graph under `/graph`) to build their route's `page.tsx` under the existing `NavShell`-wrapped layout — no further layout changes should be needed for basic navigation to reach those routes.
- The five route links (`/sources`, `/ask`, `/wiki`, `/graph`, `/settings`) currently 404 past the layout, since no `page.tsx` exists yet under those segments — this is expected and is each later plan's own scope, not a gap in this plan.
- `vitest.setup.ts`'s new Radix polyfills are available to every later Phase 6 test file without further setup.

## Self-Check: PASSED

All 5 files listed in "Files Created/Modified" verified present on disk. Both commit hashes (`e0ca3f6`, `c9d8b65`) verified present in `git log --oneline`.

---
*Phase: 06-dashboard*
*Completed: 2026-08-12*

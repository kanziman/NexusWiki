---
phase: 06-dashboard
plan: 01
subsystem: auth
tags: [nextjs, supabase-ssr, tailwind4, rls, middleware, vitest]

requires:
  - phase: 02-security-spine-and-shared-domain
    provides: RLS policies (workspaces_select_member), 0 rows -> 403/no-enumeration convention (D-12)
  - phase: 01-bootstrap-and-ground-truth
    provides: apps/dashboard scaffold (Next.js 15.5.22, Tailwind 4, TS strict, Vitest), design-tokens.css, workspacePath() helper
provides:
  - "@supabase/ssr browser/server client factories (lib/supabase/client.ts, lib/supabase/server.ts) every later Phase 6 plan imports"
  - "middleware.ts as the sole session-cookie writer and /w/[workspaceId] tenancy gate (D-02)"
  - "Email+password login (D-01) with D-12 no-enumeration error copy"
  - "/w/[workspaceId] as the RLS-scoped tenancy source of truth, reading the real workspace name via the requester's own JWT"
  - "Tailwind 4 @theme integration mapping design-tokens.css into Tailwind's utility namespace (colors/spacing/radius/font-family)"
affects: [06-02, 06-03, 06-04, 06-05, 06-06, 06-07, 06-08]

actuals:
  tokens: 22950
  tasks: 2
  commits: 3

tech-stack:
  added: ["@supabase/ssr", "@supabase/supabase-js", "@radix-ui/react-dropdown-menu", "@radix-ui/react-tooltip", "@radix-ui/react-select", "@radix-ui/react-dialog", "@radix-ui/react-tabs", "lucide-react", "cytoscape", "@types/cytoscape", "next/font/google Inter"]
  patterns:
    - "lib/supabase/{client,server}.ts as the only two places a Supabase client is constructed in apps/dashboard"
    - "middleware.ts as the sole D-02 cookie writer; RSC/Server Components never call cookies().set for auth state"
    - "Full navigation (window.location.assign) instead of router.push after auth state transitions, to avoid an RSC soft-nav / fresh-cookie race"
    - "Tailwind 4 @theme block referencing design-tokens.css custom properties via var() self-reference, relying on CSS Cascade Layers (unlayered design-tokens.css wins over @layer theme) to resolve correctly"

key-files:
  created:
    - apps/dashboard/lib/supabase/client.ts
    - apps/dashboard/lib/supabase/server.ts
    - apps/dashboard/middleware.ts
    - apps/dashboard/components/LoginForm.tsx
    - apps/dashboard/app/(auth)/login/page.tsx
    - apps/dashboard/app/w/[workspaceId]/layout.tsx
    - apps/dashboard/app/w/[workspaceId]/page.tsx
    - apps/dashboard/tests/LoginForm.test.tsx
    - apps/dashboard/.env.example
    - docs/design-systems/design-tokens.css
    - docs/design-systems/design-tokens.json
  modified:
    - apps/dashboard/app/page.tsx
    - apps/dashboard/app/layout.tsx
    - apps/dashboard/app/globals.css
    - apps/dashboard/package.json
    - apps/dashboard/pnpm-lock.yaml

key-decisions:
  - "window.location.assign('/') instead of router.push('/') after sign-in — Next.js RSC soft-navigation raced ahead of the just-written session cookie in real-browser testing; full navigation is a plan-sanctioned alternative (Task 1 <behavior>)"
  - "Committed docs/design-systems/design-tokens.css and design-tokens.json to git for the first time — they existed only in the working tree from a prior session and every Phase 6 plan depends on them being versioned"
  - "@theme color keys reference the same-named design-tokens.css custom property via var() (self-referencing by name); this resolves correctly (not a cycle) because Tailwind's @theme compiles into @layer theme, and CSS Cascade Layers give the unlayered design-tokens.css declaration unconditional priority — verified empirically, not just by spec-reading"
  - "Added app/w/[workspaceId]/page.tsx (not in the plan's files_modified list) — without a page.tsx sibling, Next.js App Router has no component to render for that route segment and /w/[workspaceId] would 404 regardless of the layout"

patterns-established:
  - "Every Supabase client construction goes through lib/supabase/client.ts (browser) or lib/supabase/server.ts (RSC) — never inline createBrowserClient/createServerClient calls elsewhere"
  - "Auth-state transitions use full navigation, not client-side router.push, to avoid cookie/RSC-cache races"

requirements-completed: [UI-01]

coverage:
  - id: D1
    description: "Unauthenticated GET /w/{any-id} redirects to /login; authenticated GET /login redirects away — middleware.ts is the sole cookie writer (D-02)"
    requirement: UI-01
    verification:
      - kind: manual_procedural
        ref: "curl -D - http://127.0.0.1:3100/w/{uuid} (unauth, 307->/login) and curl with session cookie header on /login (authenticated, 307->/) against local supabase start"
        status: pass
    human_judgment: true
    rationale: "Next.js middleware isn't unit-testable via Vitest (project's own vitest.config.ts notes RSC/middleware testing is out of scope for this harness); verified manually against the running local stack this session but no automated regression test guards it going forward."
  - id: D2
    description: "LoginForm: empty fields disable submit; wrong credentials render the exact D-12 error copy in a data-state=\"error\" region; correct credentials trigger navigation; password hint text is present"
    requirement: UI-01
    verification:
      - kind: unit
        ref: "apps/dashboard/tests/LoginForm.test.tsx (4 tests: disabled-when-empty, wrong-credentials-error-copy, correct-credentials-navigates, password-hint-text)"
        status: pass
    human_judgment: false
  - id: D3
    description: "A signed-in user landing on /w/[workspaceId] sees that workspace's real name, fetched via an RLS-scoped direct PostgREST read using their own session"
    requirement: UI-01
    verification:
      - kind: manual_procedural
        ref: "Throwaway test account + workspace created via Supabase admin API, curl with the session cookie against /w/{real-id} returned 200 with the real workspace name in the HTML; /w/{nonexistent-id} redirected to / (D-12 no-enumeration); both accounts deleted after verification"
        status: pass
    human_judgment: true
    rationale: "Requires a live Supabase stack, a real auth session, and RLS enforcement; not covered by an automated CI test in this plan (Server Components can't be rendered by the project's Vitest setup)."
  - id: D4
    description: "Tailwind 4 @theme block maps design-tokens.css into Tailwind's utility namespace; login submit button is the only accent-colored element on the screen (UI-SPEC Primary Visual Anchor)"
    requirement: UI-01
    verification:
      - kind: manual_procedural
        ref: "Production build CSS static analysis (grep of compiled .next CSS for --color-primary resolution) + Playwright script (ad hoc, not committed) using getComputedStyle to confirm exactly one #ff385c-colored element on the enabled login screen; screenshot captured"
        status: pass
    human_judgment: true
    rationale: "No automated visual-regression test exists in this plan; verified via a one-off script and screenshot during execution."
  - id: D5
    description: "No file under apps/dashboard/ reads or writes localStorage/sessionStorage for auth state (prohibition, UI-01 must_haves)"
    requirement: UI-01
    verification:
      - kind: other
        ref: "grep -rn localStorage|sessionStorage apps/dashboard (excluding node_modules) returns 0 matches"
        status: pass
    human_judgment: false

duration: ~40min active implementation (Task 1 + Task 2), plus a blocking-human package-legitimacy checkpoint wait and one session-limit interruption/resume spanning the gap between commits
completed: 2026-08-12
status: complete
---

# Phase 6 Plan 1: Auth Tracer and Design Token Integration Summary

**Email+password login via `@supabase/ssr`, `middleware.ts` as the sole D-02 session-cookie writer, and `/w/[workspaceId]` reading real workspace data through RLS with the requester's own JWT — plus the Tailwind 4 `@theme` integration every later Phase 6 component consumes.**

## Performance

- **Duration:** ~40 min active implementation across Task 1 (tracer) and Task 2 (design tokens), interrupted by the Task 0 human-verify checkpoint (package legitimacy, approved) and one session-limit cutoff/resume
- **Task 1 committed:** 2026-08-12T15:33:41+09:00
- **Task 2 committed:** 2026-08-12T15:41:33+09:00
- **Wrap-up resumed and completed:** 2026-08-12 (post session-limit reset)
- **Tasks:** 2 (Task 0 was a checkpoint, not an implementation task)
- **Files modified:** 16 (11 created, 5 modified) across the two feature commits, plus 1 unrelated `.gitignore` chore commit

## Accomplishments

- Proved the whole auth/tenancy chain end-to-end on one real path: unauthenticated `/w/{id}` -> `/login` -> sign in -> `/` (resolves the caller's own workspace via RLS) -> `/w/[workspaceId]` showing the real workspace name, all against the running local `supabase start` stack with a throwaway admin-API test account (cleaned up afterward).
- Established the two Supabase client factories (`lib/supabase/client.ts`, `lib/supabase/server.ts`) and `middleware.ts` as the sole cookie writer (D-02) that every later Phase 6 plan will import/rely on.
- Found and fixed a real race condition during manual verification: `router.push("/")` right after `signInWithPassword` could soft-navigate before the fresh session cookie was recognized server-side, occasionally rendering `/` as unauthenticated immediately after a successful login. Switched to `window.location.assign("/")` (a full navigation), which the plan's own `<behavior>` text explicitly allows as an alternative to `router.push`.
- Wired Tailwind 4's `@theme` block to consume `docs/design-systems/design-tokens.css` (colors/spacing/radius/font-family), restyled the login screen off the `.airbnb-input`/`.btn-primary` first-pass classes and onto the new Tailwind utilities, and confirmed via compiled-CSS inspection plus a one-off Playwright script that the self-referencing `var()` pattern in `@theme` resolves correctly (CSS Cascade Layers give the unlayered `design-tokens.css` declaration priority over the same-named `@layer theme` one) and that the login submit button is the screen's sole accent-colored element.
- Committed `docs/design-systems/design-tokens.css`/`.json` to git for the first time — they existed only in an untracked working-tree state from a prior session, and this plan's own Task 2 modifies the file.

## Task Commits

Each task was committed individually (Task 1's TDD test-then-implementation ended up in a single commit — see "Deviations" below for why):

1. **Task 1: End-to-end "sign in and see your workspace" tracer** - `784a22b` (feat) — includes the `tests/LoginForm.test.tsx` written first (RED, verified failing via `vitest run` before any implementation existed) and the full implementation (GREEN, verified passing) in one commit.
2. **Task 2: Design tokens `@theme` integration + auth screen visual polish** - `b48c3f9` (feat)

**Unrelated chore (same session, not a plan task):** `bffb6ac` (chore) — `.gitignore` addition of `.gstack/` from an earlier browser-tool invocation this session.

**Plan metadata:** _(this commit, follows below)_

## Files Created/Modified

- `apps/dashboard/lib/supabase/client.ts` - Browser Supabase client factory (only place `createBrowserClient` is called)
- `apps/dashboard/lib/supabase/server.ts` - RSC Supabase client factory (requester-JWT-scoped reads)
- `apps/dashboard/middleware.ts` - Sole session-cookie writer + `/w/[workspaceId]`/`/login` tenancy gate (D-02)
- `apps/dashboard/components/LoginForm.tsx` - Email+password form, D-12 no-enumeration error copy, full-navigation on success
- `apps/dashboard/app/(auth)/login/page.tsx` - `/login` route wrapper
- `apps/dashboard/app/page.tsx` - Root route: resolves the caller's own workspace via RLS-scoped read, redirects
- `apps/dashboard/app/w/[workspaceId]/layout.tsx` - Reads the workspace by id (RLS), renders its real name; D-12 uniform redirect on 0 rows
- `apps/dashboard/app/w/[workspaceId]/page.tsx` - Minimal placeholder page.tsx (required for the route segment to render at all; content lands in later plans)
- `apps/dashboard/app/layout.tsx` - `next/font/google` Inter loading
- `apps/dashboard/app/globals.css` - Tailwind 4 `@theme` block, `design-tokens.css` import, `--font-family-base` override
- `apps/dashboard/tests/LoginForm.test.tsx` - Vitest + Testing Library, 4 tests
- `apps/dashboard/.env.example` - `NEXT_PUBLIC_SUPABASE_URL`/`_PUBLISHABLE_KEY`/`NEXT_PUBLIC_API_URL`
- `apps/dashboard/package.json`, `apps/dashboard/pnpm-lock.yaml` - 10 new dependencies (Task 0 approved)
- `docs/design-systems/design-tokens.css` - New `--color-success-text`/`--color-warning-text`; committed to git for the first time
- `docs/design-systems/design-tokens.json` - Committed to git for the first time (sibling machine-readable token file)

## Decisions Made

- `window.location.assign("/")` instead of `router.push("/")` after sign-in — see Accomplishments/Deviations for the race condition this fixes.
- `docs/design-systems/design-tokens.css`/`.json` committed to git (previously untracked working-tree-only files from a prior session) — Phase 6's entire design system depends on this file existing in version control.
- `@theme` color keys use a same-named `var()` self-reference into `design-tokens.css`'s unlayered `:root` declaration, relying on CSS Cascade Layers semantics (unlayered wins over `@layer theme` unconditionally) rather than duplicating literal hex values — keeps `design-tokens.css` the single source of truth.
- Added `app/w/[workspaceId]/page.tsx` as a minimal placeholder — required for the route to render (Next.js App Router needs a `page.tsx` per segment), not listed in the plan's `files_modified` but necessary for the plan's own `<done>` criterion to be satisfiable.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `router.push` race between RSC soft-navigation and the freshly-written session cookie**
- **Found during:** Task 1, manual verification against the local `supabase start` stack
- **Issue:** Immediately after `signInWithPassword` resolved, `router.push("/")` occasionally rendered `/` as unauthenticated (the "워크스페이스가 없습니다" no-workspace message) even for a correct login — a real HTTP request with the session cookie attached (verified via `curl`) always redirected correctly, but the client-side soft navigation sometimes raced ahead.
- **Fix:** Replaced `router.push("/")` with `window.location.assign("/")`, forcing a full HTTP navigation that always carries the fresh cookie. The plan's own Task 1 `<behavior>` text explicitly names "router.push (or full navigation)" as acceptable, so this is within the plan's stated scope, not an architectural deviation.
- **Files modified:** `apps/dashboard/components/LoginForm.tsx`, `apps/dashboard/tests/LoginForm.test.tsx` (mock updated from `next/navigation`'s `useRouter` to a stubbed `window.location.assign`)
- **Verification:** Repro'd the failure and the fix via `curl` simulating the exact GoTrue password-grant call plus session-cookie replay against `/`, `/login`, `/w/{real-id}`, and `/w/{nonexistent-id}` — all four now behave correctly and deterministically.
- **Committed in:** `784a22b`

**2. [Rule 3 - Blocking] `app/w/[workspaceId]/page.tsx` missing**
- **Found during:** Task 1
- **Issue:** The plan's `<action>` only specifies `app/w/[workspaceId]/layout.tsx`; without a sibling `page.tsx`, Next.js App Router has no component to render for that route segment, so `/w/[workspaceId]` would 404 even with a correct layout — directly blocking the plan's own `<done>` criterion ("lands on `/w/[workspaceId]` showing that workspace's real name").
- **Fix:** Added a minimal placeholder `page.tsx` with a one-line Korean note that real content lands in later, dependent plans (06-02+).
- **Files modified:** `apps/dashboard/app/w/[workspaceId]/page.tsx` (new)
- **Verification:** `next build` produces a working `/w/[workspaceId]` route; curl-based E2E check renders the workspace name correctly.
- **Committed in:** `784a22b`

**3. [Rule 2 - Missing Critical] `docs/design-systems/design-tokens.css`/`.json` were never committed to git**
- **Found during:** Task 2, before staging changes
- **Issue:** Both files existed only in the working tree (from an unrelated prior session), confirmed via `git log -- docs/design-systems/design-tokens.css` (no history) and `git status` (`??`). Every Phase 6 plan's design system depends on this file's existence; leaving it permanently untracked would silently break a fresh checkout.
- **Fix:** Committed both files alongside the Task 2 `@theme` changes.
- **Files modified:** `docs/design-systems/design-tokens.css`, `docs/design-systems/design-tokens.json` (both newly tracked)
- **Verification:** `git log -- docs/design-systems/` now shows history starting at `b48c3f9`.
- **Committed in:** `b48c3f9`

---

**Total deviations:** 3 auto-fixed (1 bug, 1 blocking, 1 missing-critical)
**Impact on plan:** All three were necessary for the plan's stated `<done>` criteria to be achievable at all, or for the codebase to be in a coherent, cloneable state. No scope creep — no Phase 6 functionality beyond this plan's stated scope (06-02+ content) was added.

## Issues Encountered

- **TDD RED/GREEN gate not cleanly separated into two commits.** Task 1 carries `tdd="true"`. I wrote `tests/LoginForm.test.tsx` first and confirmed it failed for the right reason (`Failed to resolve import "@/components/LoginForm"` — the component didn't exist yet) before writing any implementation — the RED verification genuinely happened. However, the RED-only commit attempt was interrupted by a pre-commit hook failure (prettier reformatted the file, causing the hook to exit non-zero and abort the commit), and rather than re-attempting a test-only commit afterward, I proceeded directly to implementing the full tracer and committed test+implementation together in `784a22b`. See **TDD Gate Compliance** below.
- **Root-level `pnpm-workspace.yaml` stub, self-inflicted.** An early `pnpm --filter @nexuswiki/dashboard add -D @types/cytoscape` command, run from the repo root instead of `apps/dashboard`, failed with "No projects found" and left behind a broken auto-generated `/pnpm-workspace.yaml` stub (`allowBuilds: {sharp: "set this to true or false", ...}` — literal placeholder text, not valid config). This file also caused `pnpm --filter` to stop working from the repo root entirely (pnpm started treating the repo root as an empty workspace). Deleted it rather than committing it — the correct, documented config already lives at `apps/dashboard/pnpm-workspace.yaml`, and this project's dashboard is intentionally its own isolated pnpm workspace (per `01-CONTEXT.md` D-09/D-10), not part of a root-level one. Confirmed `cd apps/dashboard && pnpm ...` is unaffected.
- **Session interruption.** This execution was cut off mid-wrap-up by a session/API limit and resumed later. No work was lost — both feature commits (`784a22b`, `b48c3f9`) were already on disk; the resume only needed to complete SUMMARY.md, state updates, and a couple of pending non-plan housekeeping items (`.gitignore`, the stray `pnpm-workspace.yaml`).
- **Constraint change mid-session: stopped using the `gstack`-branded `browse` skill for verification.** I used it once (successfully, and it's how I found the `router.push` race) before an instruction arrived mid-task to avoid gstack-branded skills going forward. All verification after that point used plain `curl` (server-side behavior, including the fixed full-navigation path — a full navigation is just a fresh HTTP request, so `curl` with a replayed session cookie is a faithful equivalent) and a Playwright script driven directly via Bash/Node (reusing an already-installed Playwright + downloaded Chromium from an unrelated sibling project on this machine, no new browser download) for the `@theme` CSS cascade verification and screenshot. `.gstack/` (created by the one early `browse` invocation) was added to `.gitignore` rather than deleted, per instruction.

## TDD Gate Compliance

Task 1 (`tdd="true"`) does not have a clean two-commit RED→GREEN sequence in git log:

- ✅ RED verified: `tests/LoginForm.test.tsx` was written first and confirmed to fail (`vitest run` output: `Failed to resolve import "@/components/LoginForm"`) before any implementation file existed.
- ⚠️ RED was **not** committed separately — a pre-commit hook failure on the RED-only commit attempt interrupted the intended sequence, and implementation proceeded to a single combined `feat(06-01)` commit (`784a22b`) containing both the test and the implementation.
- ✅ GREEN verified: `vitest run` (6/6 tests, including the 4 new ones) passed before `784a22b` was committed.

Net effect: the RED/GREEN discipline was followed in *practice* (test-first, verified-failing, then implemented, then verified-passing) but not preserved as two separate commits in history. No behavior risk — the final code is fully tested and passing — but a future auditor scanning for `test(...)` → `feat(...)` commit pairs on this plan will not find one.

## User Setup Required

None - no external service configuration required. `.env.example` documents the three env vars a developer needs in `.env.local` (already gitignored); values match `apps/api`'s existing `SUPABASE_URL`/`SUPABASE_PUBLISHABLE_KEY`.

## Next Phase Readiness

- `lib/supabase/client.ts`, `lib/supabase/server.ts`, and `middleware.ts` are ready for every later Phase 6 plan (06-02 workspace switching/invites, 06-03 dropzone, etc.) to import without re-deriving the auth pattern.
- The Tailwind 4 `@theme` block is ready for later plans to extend (e.g., adding more color/spacing keys as needed) — it currently only maps what Task 2 needed for the login screen; later plans should extend rather than duplicate it.
- **Blocker for future auditors:** middleware redirect behavior and the RLS-scoped workspace read have no automated regression test (both are `human_judgment: true` in this SUMMARY's `coverage:` block) — a regression here would only surface via manual re-verification or a future E2E test suite, not CI.
- 10 npm dependencies were installed once, for the whole phase, per Task 0/1 — no later Phase 6 plan should touch `package.json` again.

## Self-Check: PASSED

All 15 files listed in "Files Created/Modified" (plus this SUMMARY.md itself) verified present on disk. All 3 commit hashes (`784a22b`, `b48c3f9`, `bffb6ac`) verified present in `git log --all`.

---
*Phase: 06-dashboard*
*Completed: 2026-08-12*

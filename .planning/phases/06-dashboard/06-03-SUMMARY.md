---
phase: 06-dashboard
plan: 03
subsystem: ui
tags: [nextjs, supabase-rpc, security-definer, radix-ui, tailwind4, vitest, tdd]

requires:
  - phase: 06-dashboard
    provides: "06-01: @supabase/ssr client/server factories, middleware.ts tenancy gate, Tailwind 4 @theme tokens; 06-02: NavShell with a /settings link already wired"
provides:
  - "supabase/migrations/0014_workspace_roster_and_invite.sql — public.workspace_members_list(uuid), public.invite_workspace_member(uuid,text,text) SECURITY DEFINER RPCs (new SQLSTATEs NW404/NW409)"
  - "apps/dashboard/components/MembersList.tsx — real member roster with role badges, owner-only remove-with-confirmation"
  - "apps/dashboard/components/InviteForm.tsx — email+role invite form wired to the 0014 RPC, TDD RED/GREEN"
  - "apps/dashboard/components/SettingsMembersPanel.tsx — client wrapper coordinating MembersList/InviteForm refresh"
  - "apps/dashboard/app/w/[workspaceId]/settings/page.tsx — /settings route (D-04, dedicated page not a modal)"
affects: [06-04, 06-05, 06-06, 06-07, 06-08]

actuals:
  tokens: 7946
  tasks: 3
  commits: 6

tech-stack:
  added: []
  patterns:
    - "SECURITY DEFINER RPC pair mirroring 0001's add_owner_as_member() idiom to cross the auth.users PostgREST-exposure boundary (workspace_members_list/invite_workspace_member)"
    - "Inside a plpgsql function whose RETURNS TABLE columns share names with a target table's columns, use ON CONFLICT ON CONSTRAINT <name> instead of ON CONFLICT (col, col) — the latter is ambiguous against the RETURNS TABLE output columns in plpgsql's identifier scope"
    - "settings/page.tsx stays a pure Server Component resolving only user.id via RLS; all client-side refresh-coordination state lives in one child client wrapper (SettingsMembersPanel) instead of promoting the whole page to a client component"
    - "Do not use Tailwind max-w-xl/w-xl/h-xl (or any size utility whose key collides with this project's custom --spacing-{xs,sm,base,lg,xl,xxl,section} @theme tokens) — it resolves against --spacing-* instead of Tailwind's built-in --container-* scale; use an inline style with a literal px value instead (logged to WINDOWS.md #11 for future Phase 6 plans)"

key-files:
  created:
    - supabase/migrations/0014_workspace_roster_and_invite.sql
    - apps/dashboard/components/MembersList.tsx
    - apps/dashboard/components/SettingsMembersPanel.tsx
    - apps/dashboard/app/w/[workspaceId]/settings/page.tsx
    - apps/dashboard/tests/MembersList.test.tsx
    - apps/dashboard/components/InviteForm.tsx
    - apps/dashboard/tests/InviteForm.test.tsx
  modified: []

key-decisions:
  - "Task 0 checkpoint (add-migration vs. reduced scope) pre-resolved by the coordinator with the user's authorization before this execution began — not skipped, not auto-approved by the executor"
  - "Task 1b (apply migration 0014 locally) was executed as a real supabase db reset with actual output captured, then returned as a blocking-human checkpoint rather than auto-approved, per gate=\"blocking-human\" carve-out — user replied \"applied\"/approved before Task 2/3 proceeded"
  - "invite_workspace_member's plpgsql body qualifies auth.users.email with a table alias and uses ON CONFLICT ON CONSTRAINT workspace_members_pkey — both were required fixes (Rule 1) found via actual supabase db reset + psql execution, not caught by static review"
  - "MembersList never renders a remove button on the owner's own row — protect_owner_membership (0004) rejects an owner deleting their own membership at the DB level, so the UI doesn't offer a control that would always fail (Rule 2)"
  - "Added components/SettingsMembersPanel.tsx (not in the plan's files_modified list) as a thin client component holding the refreshToken state that coordinates MembersList/InviteForm — required because settings/page.tsx is a Server Component per the plan's own <action> and Server Components cannot hold client state (Rule 3, same category as 06-01's missing page.tsx and 06-02's jsdom polyfills)"
  - "Replaced Tailwind's max-w-xl utility with an inline style({maxWidth: '640px'}) in SettingsMembersPanel after live-browser getComputedStyle proved it resolved to 32px (this project's --spacing-xl) instead of a real container width (Rule 1) — logged as WINDOWS.md entry #11 since the same collision risk applies to any future Phase 6 use of max-w-*/w-*/h-* with a key matching xs/sm/base/lg/xl/xxl/section"

patterns-established:
  - "SECURITY DEFINER RPC pair for auth.users-crossing reads/writes, revoked from public/anon, granted to authenticated only — reusable template for any future user-lookup-by-email need"
  - "ON CONFLICT ON CONSTRAINT inside plpgsql functions with RETURNS TABLE column-name collisions"
  - "Server Component page + single client wrapper for cross-component refresh coordination"

requirements-completed: [UI-02]

coverage:
  - id: D1
    description: "Settings page renders a real member roster (role badge per member) and a dedicated invite form above it — one page, no modal (D-04)"
    requirement: UI-02
    verification:
      - kind: unit
        ref: "apps/dashboard/tests/MembersList.test.tsx — \"workspace_members_list RPC가 반환한 두 멤버의 이메일과 역할 배지를 렌더링한다\""
        status: pass
      - kind: manual_procedural
        ref: "Throwaway owner/target accounts + workspace (GoTrue admin API + docker exec psql) + plain Playwright script (not a gstack skill) against local next dev + supabase start: login -> /w/{id}/settings shows owner row with 소유자 badge. Screenshot 06-03-2-after-invite.png. Both accounts + workspace deleted after (0 rows remaining, verified)."
        status: pass
    human_judgment: true
    rationale: "The live end-to-end Playwright script was ad hoc (not committed as a CI regression test), matching the same limitation 06-01/06-02 documented for RSC/middleware behavior — a future regression in the real request path would only surface via manual re-verification."
  - id: D2
    description: "Invite role field defaults to viewer; submit is disabled only on invalid email format, never on role choice"
    requirement: UI-02
    verification:
      - kind: unit
        ref: "apps/dashboard/tests/InviteForm.test.tsx — \"이메일 형식이 올바르지 않으면 제출 버튼이 비활성화된다\" and \"역할을 건드리지 않으면 기본값이 뷰어이고, 유효한 이메일이면 제출이 활성화된다\""
        status: pass
    human_judgment: false
  - id: D3
    description: "Inviting an already-registered member surfaces the exact copy '이미 워크스페이스 멤버입니다.' (NW409); inviting an unregistered email surfaces this plan's own NW404 copy"
    requirement: UI-02
    verification:
      - kind: unit
        ref: "apps/dashboard/tests/InviteForm.test.tsx — NW409 and NW404 mocked-RPC-rejection tests"
        status: pass
      - kind: manual_procedural
        ref: "Live duplicate-invite against the local stack (real 0014 RPC, real NW409 SQLSTATE) — screenshot 06-03-3-duplicate-error.png"
        status: pass
    human_judgment: true
    rationale: "The unit test mocks the RPC error shape; the live check is what proves the real SQLSTATE (NW409/NW404) round-trips through PostgREST/Supabase JS correctly end to end — that round trip isn't exercised by CI."
  - id: D4
    description: "Removing a member requires confirming the exact copy template, and confirming calls workspace_members.delete().match({workspace_id, user_id}) with the exact pair clicked"
    requirement: UI-02
    verification:
      - kind: unit
        ref: "apps/dashboard/tests/MembersList.test.tsx — \"owner가 다른 멤버를 제거 확인 후 정확한 {workspace_id, user_id} 쌍으로 delete().match()를 호출한다\""
        status: pass
      - kind: manual_procedural
        ref: "Live removal against the local stack (real RLS-enforced delete) — screenshots 06-03-4-remove-dialog.png, 06-03-5-after-remove.png"
        status: pass
    human_judgment: true
    rationale: "Same class as D3 — the live check proves the real RLS-enforced delete path works, which the mocked unit test cannot prove on its own."
  - id: D5
    description: "The members list shows a loading/skeleton state on initial fetch before rows resolve (backstop truth)"
    requirement: UI-02
    verification:
      - kind: unit
        ref: "apps/dashboard/tests/MembersList.test.tsx — \"초기 조회 동안 스켈레톤 상태를 보여준다\""
        status: pass
    human_judgment: false
  - id: D6
    description: "Both 0014 RPCs are authenticated-only (anon denied); invite is owner-only (42501 otherwise); NW404/NW409 SQLSTATEs are literal, not just message text"
    requirement: UI-02
    verification:
      - kind: manual_procedural
        ref: "docker exec psql: has_function_privilege('anon', ...) = f for both functions; savepoint-isolated functional tests covering success/NW409/NW404/42501/roster-list, plus a DO block confirming raw SQLSTATE=NW404 via EXCEPTION WHEN OTHERS"
        status: pass
    human_judgment: true
    rationale: "DB-level ACL and SQLSTATE checks require a live local Supabase stack (docker exec psql) — not part of the Vitest/CI harness."

duration: ~20min active (this continuation: Task 2, Task 3 TDD, two live-verification bug fixes), following an earlier session covering Task 0 checkpoint pre-resolution, Task 1 migration authoring, and the Task 1b blocking-human local-apply checkpoint
completed: 2026-08-12
status: complete
---

# Phase 6 Plan 3: Member Roster and Email Invite Summary

**A working member roster + email-based invite for UI-02/D-04, closing a real backend gap (no email->user_id resolution path existed anywhere) with two new SECURITY DEFINER RPCs (migration 0014) mirroring 0001's established idiom, wired end to end through MembersList.tsx and a TDD-built InviteForm.tsx.**

## Performance

- **Duration:** ~20 min active in this continuation (Task 2, Task 3 TDD RED/GREEN, plus two live-verification bug fixes), following an earlier session for Task 0's pre-resolved checkpoint, Task 1's migration, and the Task 1b blocking-human local-apply checkpoint
- **Tasks:** 3/3 completed (Task 0 was a checkpoint, pre-resolved by coordinator authorization; Task 1b was a blocking-human checkpoint, executed and signed off before continuing)
- **Files modified:** 7 (all newly created)

## Accomplishments

- Closed the real backend gap this plan discovered: added `supabase/migrations/0014_workspace_roster_and_invite.sql` with two `SECURITY DEFINER` RPCs — `workspace_members_list` (roster with email, gated by `is_workspace_member` inside the function body) and `invite_workspace_member` (owner-only, server-revalidates the role argument, raises project-custom `NW404`/`NW409` SQLSTATEs) — mirroring `0001`'s `add_owner_as_member()` idiom exactly, no new table, no RLS change, no `service_role` anywhere.
- Found and fixed a real plpgsql bug via actual `supabase db reset` + `psql` execution (not caught by static review): `RETURNS TABLE` output columns (`user_id`, `email`, `role`) shadow same-named bare column references inside the function body, breaking both the `auth.users` lookup and the `ON CONFLICT (workspace_id, user_id)` target list with "column reference is ambiguous". Fixed with a table alias and `ON CONFLICT ON CONSTRAINT workspace_members_pkey`.
- Verified the full RPC contract with `psql` (savepoint-isolated, all rolled back): owner invites a registered target -> success row; same invite again -> `NW409`; invite of an unregistered email -> `NW404`; non-owner editor attempts invite -> `42501`; roster list returns all 3 members with emails. Confirmed raw SQLSTATEs (not just message text) via a `DO`/`EXCEPTION WHEN OTHERS` probe.
- Built `MembersList.tsx`: skeleton loading state, role badges, and an owner-only remove control that is never rendered on the owner's own row (since `protect_owner_membership` (0004) would reject that delete at the DB level) — a Rule 2 correctness addition, not a plan requirement.
- Built `InviteForm.tsx` via TDD (RED committed separately from GREEN): email-format-only submit gating, role defaults to viewer, and branches on the RPC's `PostgrestError.code` for `NW409`/`NW404`/`42501` with the UI-SPEC's exact copy.
- Added `SettingsMembersPanel.tsx` (a small client wrapper, not in the plan's file list) to hold the `refreshToken` state that lets `InviteForm`'s `onInvited` remount `MembersList` — required because `settings/page.tsx` is a Server Component per the plan and Server Components can't hold client state.
- Ran a full live end-to-end pass against the real local stack (throwaway owner/target accounts + workspace, plain Playwright — no gstack skills): login -> settings page -> invite -> roster updates -> duplicate invite shows exact NW409 copy -> remove with confirmation -> member disappears. During this pass, found and fixed a second real bug: Tailwind's `max-w-xl` utility resolved to this project's custom `--spacing-xl` (32px) instead of a real container width, collapsing the whole settings page into a single unreadably narrow column. Fixed with an inline style and logged to `WINDOWS.md` (#11) as a systemic risk for any future Phase 6 use of size utilities whose key matches this project's custom spacing-scale names.
- All throwaway test data (2 accounts, 1 workspace) deleted and verified at 0 rows remaining after verification.

## Task Commits

1. **Task 0: Decide invite backing** (checkpoint:decision) — pre-resolved to `add-migration` by the coordinator with the user's authorization; no commit (decision only)
2. **Task 1: Migration 0014** - `228e875` (feat), plus `f0ad837` (fix — ambiguous plpgsql column references, found during Task 1b's own local verification)
3. **Task 1b: Apply migration 0014 locally** (checkpoint:human-verify, `gate="blocking-human"`) — executed as a real `supabase db reset`, returned as a checkpoint with actual output, signed off by the user ("applied"/approved) before continuing
4. **Task 2: MembersList.tsx + settings page** - `cd4decc` (feat)
5. **Task 3: InviteForm.tsx (TDD)** - `35b808a` (test, RED) then `81fc108` (feat, GREEN)
6. **Live-verification bug fix: Tailwind max-w-xl collision** - `6e22327` (fix)

**Plan metadata:** _(this commit, follows below)_

## Files Created/Modified

- `supabase/migrations/0014_workspace_roster_and_invite.sql` - `workspace_members_list(uuid)`, `invite_workspace_member(uuid,text,text)` SECURITY DEFINER RPCs
- `apps/dashboard/components/MembersList.tsx` - Member roster, role badges, skeleton loading, owner-only remove-with-confirmation
- `apps/dashboard/components/SettingsMembersPanel.tsx` - Client wrapper coordinating MembersList/InviteForm refresh (not in original plan file list)
- `apps/dashboard/app/w/[workspaceId]/settings/page.tsx` - `/settings` route, Server Component resolving `user.id`
- `apps/dashboard/tests/MembersList.test.tsx` - Vitest + Testing Library, 5 tests
- `apps/dashboard/components/InviteForm.tsx` - Email+role invite form wired to the 0014 RPC
- `apps/dashboard/tests/InviteForm.test.tsx` - Vitest + Testing Library, 5 tests (TDD)

## Decisions Made

- Task 0 pre-resolved to `add-migration` by coordinator authorization (documented, not silently skipped).
- Task 1b executed as a real local `supabase db reset` (not simulated), returned as a blocking-human checkpoint with actual output rather than auto-approved.
- `ON CONFLICT ON CONSTRAINT workspace_members_pkey` instead of `ON CONFLICT (workspace_id, user_id)` inside `invite_workspace_member` — sidesteps plpgsql's identifier-scope collision with the `RETURNS TABLE` output columns.
- MembersList never offers a remove control on the owner's own row — `protect_owner_membership` (0004) would reject that delete at the DB level, so the UI doesn't present a control that always fails.
- `SettingsMembersPanel.tsx` added as the single client-state holder for refresh coordination, keeping `settings/page.tsx` a pure Server Component per the plan.
- Avoided Tailwind's `max-w-xl` (and by extension any `max-w-*`/`w-*`/`h-*` utility whose key collides with this project's custom `--spacing-{xs,sm,base,lg,xl,xxl,section}` tokens) in favor of an explicit inline style; logged to `WINDOWS.md` for future Phase 6 plans.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] plpgsql ambiguous column reference in `invite_workspace_member`**
- **Found during:** Task 1b's own local verification (`supabase db reset` + `psql`)
- **Issue:** `RETURNS TABLE` output columns (`user_id`, `email`, `role`) are implicitly in scope as plpgsql variables inside the function body, so the bare `email` in the `auth.users` lookup and the bare `(workspace_id, user_id)` in `ON CONFLICT` both raised "column reference is ambiguous".
- **Fix:** Table-aliased the `auth.users` query (`u.email`) and switched to `ON CONFLICT ON CONSTRAINT workspace_members_pkey`.
- **Files modified:** `supabase/migrations/0014_workspace_roster_and_invite.sql`
- **Verification:** Re-ran `supabase db reset` (clean) and the full 5-scenario `psql` savepoint functional test (success/NW409/NW404/42501/roster-list), all passing.
- **Committed in:** `f0ad837`

**2. [Rule 2 - Missing Critical] MembersList hides the remove control on the owner's own row**
- **Found during:** Task 2 implementation
- **Issue:** `protect_owner_membership` (0004) rejects an owner deleting their own membership row at the DB level; without a UI-side guard, the owner would see a remove button that always fails.
- **Fix:** `canRemove = isOwner && member.user_id !== currentUserId` gates the remove control's visibility.
- **Files modified:** `apps/dashboard/components/MembersList.tsx`
- **Verification:** `apps/dashboard/tests/MembersList.test.tsx` — "owner 자신의 행에는 제거 버튼을 그리지 않는다"
- **Committed in:** `cd4decc`

**3. [Rule 3 - Blocking] Added `SettingsMembersPanel.tsx` (not in the plan's file list)**
- **Found during:** Task 2 implementation
- **Issue:** The plan specifies `settings/page.tsx` as a Server Component, but `InviteForm`'s `onInvited` -> `MembersList` refresh coordination (Task 3 `<behavior>`) requires client-side state, which a Server Component cannot hold.
- **Fix:** Added a thin client wrapper holding a `refreshToken` state, passed as `MembersList`'s `key`.
- **Files modified:** `apps/dashboard/components/SettingsMembersPanel.tsx` (new), `apps/dashboard/app/w/[workspaceId]/settings/page.tsx`
- **Verification:** `tsc --noEmit` clean; live end-to-end pass confirms invite -> roster refresh works.
- **Committed in:** `cd4decc`

**4. [Rule 1 - Bug] Tailwind `max-w-xl` resolving to this project's `--spacing-xl` (32px)**
- **Found during:** Live end-to-end verification against the real dev server
- **Issue:** `globals.css`'s `@theme` block defines `--spacing-xl: 32px` but no `--container-xl`; Tailwind's compiled `max-w-xl` utility resolved against `--spacing-xl` instead of its own default `--container-xl` (36rem), collapsing the whole settings page into an unreadable ~32px-wide column (confirmed via `getComputedStyle`, `maxWidth: "32px"`). `max-w-md` (used elsewhere, the removal dialog) was independently confirmed safe (448px, matches Tailwind's default) since this project doesn't define `--spacing-md`.
- **Fix:** Replaced `max-w-xl` with an inline `style={{ maxWidth: "640px" }}`.
- **Files modified:** `apps/dashboard/components/SettingsMembersPanel.tsx`
- **Verification:** Re-ran the full live end-to-end pass; screenshot confirms correct 640px-wide layout.
- **Committed in:** `6e22327`
- **Also logged:** `.planning/WINDOWS.md` entry #11 (kind: deviation) — flags the general collision risk for any future Phase 6 use of `max-w-*`/`w-*`/`h-*` with a key matching this project's custom spacing-scale names (`xs`/`sm`/`base`/`lg`/`xl`/`xxl`/`section`).

---

**Total deviations:** 4 auto-fixed (2 bugs, 1 missing-critical, 1 blocking)
**Impact on plan:** All four were necessary for the plan's own `<done>`/`<acceptance_criteria>` to be genuinely satisfiable (a working RPC, a UI that doesn't offer buttons that always fail, a refresh mechanism the plan's own behavior spec requires, and a readable page) or were found and fixed as a direct result of actually running the plan's own verification steps rather than trusting static review. No scope creep — no Phase 6 functionality beyond this plan's stated scope was added.

## Issues Encountered

- **Own test-authoring bug (not a plan/component issue):** the first draft of both `InviteForm.test.tsx`'s role-default assertion and the live Playwright script queried `getByText("뷰어")`/`getByText("소유자")`, which matched Radix Select's visually-hidden native `<select><option>` fallback in addition to the visible trigger, causing a "strict mode violation: resolved to 2 elements" failure. Fixed by scoping the query to the visible `combobox`/`data-role` element in both the Vitest test and the debug Playwright script. Not a component bug — confirmed by direct DOM inspection.
- **Session-boundary checkpoint:** Task 1b (`gate="blocking-human"`) was correctly not auto-approved despite auto-mode considerations elsewhere — the executor ran the real `supabase db reset` itself, returned the actual output as a checkpoint, and only proceeded to Task 2/3 after the coordinator relayed the user's "applied"/approved response.

## User Setup Required

None — no external service configuration required. Local Supabase stack (`supabase_db_NexusWiki`, already running) was used for all verification; no cloud push was performed.

## Next Phase Readiness

- UI-02 is fully satisfied end to end: workspace switching (06-02) + member roster + email invite + role assignment + member removal, all live-verified against the real local stack, not a UI shell over a missing backend.
- `supabase/migrations/0014_workspace_roster_and_invite.sql` has NOT been pushed to the cloud project — only applied locally via `supabase db reset`. A future session must run the project's documented cloud-push runbook (`HANDOFF.md`) before this capability is live in production; once pushed, migration `0014`'s function signatures become permanently fixed per this project's append-only-after-push convention.
- `MembersList.tsx`/`InviteForm.tsx`/`SettingsMembersPanel.tsx` establish the SECURITY DEFINER RPC + Server-Component-page/client-wrapper patterns any later Phase 6 plan needing a similar "cross a PostgREST-unexposed-schema boundary" or "coordinate refresh between sibling client components" need can reuse directly.
- **Blocker for future auditors:** the D1/D3/D4/D6 coverage entries are `human_judgment: true` — the live Playwright/psql verification this session performed is not committed as an automated regression test, matching the same limitation 06-01/06-02 documented for RSC/middleware/RLS behavior.
- **Tracked defect (not blocking):** `.planning/WINDOWS.md` #11 — any future Phase 6 plan using a Tailwind size utility (`max-w-*`/`w-*`/`h-*`) with a key matching this project's custom spacing-scale names (`xs`/`sm`/`base`/`lg`/`xl`/`xxl`/`section`) should verify the resolved value with `getComputedStyle` before trusting it, since it may silently resolve against `--spacing-*` instead of Tailwind's built-in `--container-*`/size scale.

## Self-Check: PASSED

All 7 files listed in "Files Created/Modified" verified present on disk. All 6 commit hashes (`228e875`, `f0ad837`, `cd4decc`, `35b808a`, `81fc108`, `6e22327`) verified present in `git log --all`. `pnpm exec vitest run` (20/20 passing) and `pnpm exec tsc --noEmit` (clean) both re-confirmed before writing this summary.

---
*Phase: 06-dashboard*
*Completed: 2026-08-12*

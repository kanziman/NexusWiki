---
phase: 06-dashboard
fixed_at: 2026-08-12T00:00:00Z
review_path: .planning/phases/06-dashboard/06-REVIEW.md
iteration: 1
findings_in_scope: 6
fixed: 6
skipped: 0
status: all_fixed
---

# Phase 6: Code Review Fix Report

**Fixed at:** 2026-08-12T00:00:00Z
**Source review:** `.planning/phases/06-dashboard/06-REVIEW.md`
**Iteration:** 1

**Summary:**
- Findings in scope: 6 (Critical: 1, Warning: 5 — `fix_scope: critical_warning`, so the 2 Info findings were not attempted)
- Fixed: 6
- Skipped: 0

**Verification:** `npx vitest run` (77/77 passing) and `npx tsc --noEmit` (no errors) both run in the main working tree (`apps/dashboard/`) after every commit — `workflow.use_worktrees=false` per this run's constraints, so all edits and commits landed directly on `main`, no worktree was created, and there is no isolation/reproducibility gap between what was verified and what is now on disk.

## Fixed Issues

### CR-01: Red-link "지금 생성" CTA prefill/tab query params are never consumed

**Files modified:** `apps/dashboard/app/w/[workspaceId]/sources/page.tsx`, `apps/dashboard/components/SourcesList.tsx`, `apps/dashboard/components/Dropzone.tsx`
**Commit:** `86d545f`
**Applied fix:** `SourcesPage` now declares and reads `searchParams` (`prefillTitle`, `tab`) and passes `prefillTitle`/`initialTab` to `SourcesList`, which forwards them to `Dropzone` as new optional props. `Dropzone` seeds its `tab` state from `initialTab ?? "file"` and its `textTitle` state from `prefillTitle ?? ""` on mount, matching the review's suggested fix exactly. No existing test asserted the old (broken) behavior, so no test changes were needed for this finding.

### WR-01: Graph node-cap notice has an off-by-one false positive

**Files modified:** `apps/dashboard/components/GraphCanvas.tsx`
**Commit:** `cae2840`
**Applied fix:** `capped` now uses `count !== null ? count > PAGE_ROW_CAP : nodes.length === PAGE_ROW_CAP` instead of OR-ing the exact-count and page-length heuristics — the length fallback only applies when `count` is unavailable, so a workspace with exactly 1,000 wiki pages no longer trips the cap banner.

### WR-02: Ask SSE fetch doesn't check `response.ok`

**Files modified:** `apps/dashboard/components/AskConversation.tsx`, `apps/dashboard/tests/AskConversation.test.tsx`
**Commit:** `ea9c0c0`
**Applied fix:** `submitQuestion` now checks `response.ok` before entering the `parseSseStream` loop. On a non-2xx response it reads a best-effort `detail` token from the JSON body (via a new `readAskErrorToken` helper, modeled on `api-client.ts`'s `parseJsonBody`) and patches the turn directly to the existing `status: "error"` card/retry-button path, instead of falling through to the generic "connection dropped" message. Updated the test's global `fetch` mock to return `{ ok: true }` so the 6 existing success-path assertions keep exercising the SSE branch (this is a required test-mock fidelity fix, not a scope-creep change — the tests still assert the same behaviors as before).

### WR-03: `MembersList` treats an RLS-blocked delete as a successful removal

**Files modified:** `apps/dashboard/components/MembersList.tsx`, `apps/dashboard/tests/MembersList.test.tsx`
**Commit:** `6c21ce2`
**Applied fix:** `handleConfirmRemove` now chains `.select()` after `.delete().match(...)` and treats `error || !data || data.length === 0` as a failure, matching the review's suggested fix. Updated the test's Supabase client mock so `match()` returns a chainable `{ select }` (previously `match` resolved directly), and added a new test asserting that a 0-row delete result (RLS-blocked case) shows the "멤버를 제거하지 못했습니다." banner and leaves the member in the local list instead of optimistically removing them. **This finding is a logic fix (state/success-detection correctness), not a pure syntax change — flagging per the fixer's verification-strategy note for human confirmation that the RLS-blocked-delete semantics are exactly right in production, even though both the type checker and the new/updated unit tests pass.**

### WR-04: `JobStepper` polls forever, even after every job reaches a terminal state

**Files modified:** `apps/dashboard/components/JobStepper.tsx`
**Commit:** `cf1eb07`
**Applied fix:** The polling interval handle now lives in a ref (`pollTimerRef`); after each successful poll, if every `STAGE_TYPES` job is in `TERMINAL_STATUSES`, the interval is cleared. Went one step further than the review's literal suggestion: since retry/cancel actions can move a job back out of a terminal state (dead → queued, running → canceled), `handleRetry`/`handleConfirmCancel` now call `resumePollingIfStopped()` + an immediate `poll()` after their POST succeeds, so those actions don't leave the stepper stuck on stale state after polling had already stopped. Also replaced the closure-local `cancelled` flag (no longer expressible now that `poll` is a component-level `useCallback` shared by the effect and the action handlers) with a `mountedRef`, preserving the original "don't setState after unmount" guarantee. **This finding is a logic fix (async timer/state-machine correctness), not a pure syntax change — flagging per the fixer's verification-strategy note for human confirmation, particularly around the retry/cancel-resumes-polling behavior, which the existing test suite doesn't exercise (no test drives the interval across multiple ticks).**

### WR-05: Inconsistent / missing fail-fast validation for `NEXT_PUBLIC_*` env vars

**Files modified:** `apps/dashboard/lib/env.ts` (new), `apps/dashboard/lib/supabase/client.ts`, `apps/dashboard/lib/supabase/server.ts`, `apps/dashboard/middleware.ts`, `apps/dashboard/lib/api-client.ts`, `apps/dashboard/components/AskConversation.tsx`, `apps/dashboard/tests/AskConversation.test.tsx`
**Commit:** `57b75c6`
**Applied fix:** Added `requireEnv(name)` in a new `lib/env.ts` (matches the review's suggested signature exactly) and replaced all five flagged call sites — the two `!` non-null assertions in `client.ts`/`server.ts`, the third in `middleware.ts` (present in the finding's file list but not shown in the review's code excerpt), and the two unguarded template-string interpolations in `api-client.ts` and `AskConversation.tsx`. A missing env var now throws `Missing required environment variable: <NAME>` at first use instead of an opaque Supabase SDK error or a request silently going to `"undefined/..."`. Added `process.env.NEXT_PUBLIC_API_URL` setup/teardown to `AskConversation.test.tsx`'s `beforeEach`/`afterEach` (same pattern already used in `api-client.test.ts`) since the real `apiFetch`/`fetch` call sites now require it to be set; all other test files mock `@/lib/supabase/client` and `@/lib/api-client` entirely, so `requireEnv` never executes on those paths and no other tests needed changes.

## Skipped Issues

None — all 6 in-scope findings (Critical: 1, Warning: 5) were fixed.

---

_Fixed: 2026-08-12T00:00:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_

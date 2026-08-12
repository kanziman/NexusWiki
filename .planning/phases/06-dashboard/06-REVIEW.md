---
phase: 06-dashboard
reviewed: 2026-08-12T00:00:00Z
depth: standard
files_reviewed: 56
files_reviewed_list:
  - .gitignore
  - apps/dashboard/.env.example
  - apps/dashboard/app/(auth)/login/page.tsx
  - apps/dashboard/app/globals.css
  - apps/dashboard/app/layout.tsx
  - apps/dashboard/app/page.tsx
  - apps/dashboard/app/w/[workspaceId]/ask/page.tsx
  - apps/dashboard/app/w/[workspaceId]/graph/page.tsx
  - apps/dashboard/app/w/[workspaceId]/layout.tsx
  - apps/dashboard/app/w/[workspaceId]/page.tsx
  - apps/dashboard/app/w/[workspaceId]/settings/page.tsx
  - apps/dashboard/app/w/[workspaceId]/sources/page.tsx
  - apps/dashboard/app/w/[workspaceId]/wiki/[slug]/page.tsx
  - apps/dashboard/app/w/[workspaceId]/wiki/page.tsx
  - apps/dashboard/components/AskConversation.tsx
  - apps/dashboard/components/CitationMarker.tsx
  - apps/dashboard/components/CitationSidePanel.tsx
  - apps/dashboard/components/Dropzone.tsx
  - apps/dashboard/components/GraphCanvas.tsx
  - apps/dashboard/components/GraphLensFilter.tsx
  - apps/dashboard/components/InviteForm.tsx
  - apps/dashboard/components/JobStepper.tsx
  - apps/dashboard/components/LoginForm.tsx
  - apps/dashboard/components/MembersList.tsx
  - apps/dashboard/components/NavShell.tsx
  - apps/dashboard/components/RedLinkCta.tsx
  - apps/dashboard/components/SettingsMembersPanel.tsx
  - apps/dashboard/components/SourcesList.tsx
  - apps/dashboard/components/WikiPageContent.tsx
  - apps/dashboard/components/WorkspaceSwitcher.tsx
  - apps/dashboard/lib/api-client.ts
  - apps/dashboard/lib/citation-anchors.ts
  - apps/dashboard/lib/sse.ts
  - apps/dashboard/lib/supabase/client.ts
  - apps/dashboard/lib/supabase/server.ts
  - apps/dashboard/lib/wiki-links.ts
  - apps/dashboard/middleware.ts
  - apps/dashboard/package.json
  - apps/dashboard/tests/AskConversation.test.tsx
  - apps/dashboard/tests/CitationMarker.test.tsx
  - apps/dashboard/tests/Dropzone.test.tsx
  - apps/dashboard/tests/GraphLensFilter.test.tsx
  - apps/dashboard/tests/InviteForm.test.tsx
  - apps/dashboard/tests/JobStepper.test.tsx
  - apps/dashboard/tests/LoginForm.test.tsx
  - apps/dashboard/tests/MembersList.test.tsx
  - apps/dashboard/tests/RedLinkCta.test.tsx
  - apps/dashboard/tests/WorkspaceSwitcher.test.tsx
  - apps/dashboard/tests/api-client.test.ts
  - apps/dashboard/tests/citation-anchors.test.ts
  - apps/dashboard/tests/sse.test.ts
  - apps/dashboard/tests/wiki-links.test.ts
  - apps/dashboard/vitest.setup.ts
  - docs/design-systems/design-tokens.css
  - docs/design-systems/design-tokens.json
  - supabase/migrations/0014_workspace_roster_and_invite.sql
findings:
  critical: 1
  warning: 5
  info: 2
  total: 8
status: issues_found
---

# Phase 6: Code Review Report

**Reviewed:** 2026-08-12T00:00:00Z
**Depth:** standard
**Files Reviewed:** 56
**Status:** issues_found

## Summary

Reviewed the Phase 6 dashboard surface (Next.js 15 App Router, Supabase RLS-backed reads,
apps/api writes) plus the one accompanying migration (`0014`) and design-token assets. The
codebase is disciplined about the RLS-first tenancy model (no `service_role` on user paths,
consistent no-enumeration behavior, careful anchor/citation handling to prevent premature
trust of unresolved anchors) and the test suite is thorough for the individual components it
covers.

The most significant finding is a genuine cross-file integration gap: `RedLinkCta`'s "지금
생성" (create now) action constructs a URL with `?prefillTitle=…&tab=text`, but nothing in the
destination route chain (`sources/page.tsx` → `SourcesList` → `Dropzone`) ever reads those
query parameters — the feature silently does nothing beyond navigating to a blank Dropzone on
the default "file" tab. This is a "component's own tests pass, integration is untested" class
of bug that only shows up when tracing the full navigation chain, which is exactly what this
review depth is meant to catch.

Other findings are narrower: an off-by-one in the graph node-cap notice, a silent
false-success path when a client-side Supabase `delete()` is blocked by RLS, unchecked
HTTP status on the Ask SSE fetch (server errors get miscategorized as "connection dropped"),
an unbounded 3s polling loop that never stops once a job chain reaches a terminal state, and
inconsistent environment-variable validation that contradicts the project's documented
fail-fast convention.

## Critical Issues

### CR-01: Red-link "지금 생성" CTA prefill/tab query params are never consumed

**File:** `apps/dashboard/components/RedLinkCta.tsx:36-43`
**Issue:** `handleCreate()` navigates to
`` `${workspacePath(workspaceId)}/sources?prefillTitle=${encodeURIComponent(title)}&tab=text` ``,
explicitly documented (and unit-tested in `tests/RedLinkCta.test.tsx`) as prefilling the
Dropzone's text tab with the red-link's title so the user can immediately create the missing
page. However:

- `apps/dashboard/app/w/[workspaceId]/sources/page.tsx:4-27` types `SourcesPageProps` with
  only `params` — it never declares or reads `searchParams`, so `prefillTitle`/`tab` are
  dropped at the route boundary.
- `apps/dashboard/components/SourcesList.tsx:18-21` (`SourcesListProps`) has no
  title/tab-related prop to forward anything even if the page did read the params.
- `apps/dashboard/components/Dropzone.tsx:9-12` (`DropzoneProps`) accepts only
  `{ workspaceId, onIngested }` — there is no prop to set an initial tab or pre-populate the
  title field; the component's internal `tab` state always initializes to `"file"`
  (`useState<TabValue>("file")` at line 69).

Confirmed via repo-wide grep: `prefillTitle` and `tab=` only ever appear in `RedLinkCta.tsx`
and its test — there is no consumer anywhere in `apps/dashboard/app` or
`apps/dashboard/components`. Clicking "지금 생성" therefore just lands the user on the Sources
page's default File tab with an empty form; the title they were trying to create is lost and
they must retype it after manually switching to the Text tab. This is the actual advertised
behavior of the feature (per the inline plan citation and the existing unit test's own
description), so it is a genuine functional regression, not a documented deferral.

**Fix:** Wire the query params through the chain, e.g.:
```tsx
// app/w/[workspaceId]/sources/page.tsx
type SourcesPageProps = {
  params: Promise<{ workspaceId: string }>;
  searchParams: Promise<{ prefillTitle?: string; tab?: string }>;
};

export default async function SourcesPage({ params, searchParams }: SourcesPageProps) {
  const { workspaceId } = await params;
  const { prefillTitle, tab } = await searchParams;
  // ...
  return (
    <SourcesList
      workspaceId={workspaceId}
      initialSources={data ?? []}
      prefillTitle={prefillTitle}
      initialTab={tab === "text" ? "text" : undefined}
    />
  );
}
```
and thread `prefillTitle`/`initialTab` down into `Dropzone` as new optional props that seed
`tab`/`textTitle` state on mount.

## Warnings

### WR-01: Graph node-cap notice has an off-by-one false positive

**File:** `apps/dashboard/components/GraphCanvas.tsx:104-106`
**Issue:**
```ts
const capped =
  (count !== null && count > PAGE_ROW_CAP) ||
  nodes.length === PAGE_ROW_CAP;
```
The comment above this code explicitly states the intent: use the exact `count` (from
`{ count: "exact" }`) to distinguish "exactly 1,000 wiki pages total" from "capped at 1,000,
more exist". But the `||` with `nodes.length === PAGE_ROW_CAP` defeats that intent: when a
workspace has exactly 1,000 wiki pages (not one more), `count === 1000` so the first clause is
false, but `nodes.length` is also exactly `1000`, so the second clause is true and the cap
banner (`"이 워크스페이스는 그래프 표시 한도(1,000개 노드)를 초과했습니다…"`) is shown even
though the graph is not actually truncated.
**Fix:** Only fall back to the length heuristic when `count` is unavailable:
```ts
const capped =
  count !== null ? count > PAGE_ROW_CAP : nodes.length === PAGE_ROW_CAP;
```

### WR-02: Ask SSE fetch doesn't check `response.ok` — server errors are miscategorized as "connection dropped"

**File:** `apps/dashboard/components/AskConversation.tsx:129-144`
**Issue:** The raw `fetch()` call to `/workspaces/{id}/ask` is used instead of `apiFetch`
(justified in the surrounding comment purely by the SSE response shape), but the code never
checks `response.ok`/`response.status` before handing the response to `parseSseStream`. If the
backend returns a non-SSE JSON error body for a 401/402/403/500 (e.g. `{"detail":"forbidden"}`
with no `event:`/`data:` lines and no trailing `\n\n`), `parseSseStream`
(`apps/dashboard/lib/sse.ts:39-51`) never finds a frame boundary and silently yields zero
events. The `for await` loop then falls through to `finally`, which — because the turn never
left `"streaming"` — sets `status: "dropped"` and shows the generic
`"연결이 끊어졌습니다. 다시 시도해주세요."` message with a retry button, even though retrying
a genuine 403/402 will just fail again for the same reason. Real, actionable error information
(budget exceeded, forbidden, etc., which `Dropzone`'s `mapIngestError` deliberately surfaces
for the sibling ingest endpoints) is lost here.
**Fix:** Check `response.ok` before entering the SSE loop and branch to a distinct error state
(or reuse `ApiError`-style status/detail parsing) instead of letting it fall through to the
generic "dropped" path.

### WR-03: `MembersList` treats an RLS-blocked delete as a successful removal

**File:** `apps/dashboard/components/MembersList.tsx:83-107`
**Issue:** `handleConfirmRemove` calls
`supabase.from("workspace_members").delete().match({ workspace_id, user_id })` and only checks
`error`. Per this project's own documented Postgres/RLS behavior (CLAUDE.md "Error Handling":
*"An RLS `USING` failure on UPDATE/DELETE returns 0 rows, not an exception"*), a delete blocked
by `workspace_members_delete_owner` RLS returns `error: null` with zero affected rows — no
exception is thrown. Since the code doesn't request the deleted rows back (no `.select()`) or
otherwise verify the affected-row count, any 0-row outcome (a role changed out from under the
UI, a stale `isOwner` computation, a race with another admin) is treated identically to a real
success: the member is optimistically removed from local state and the dialog closes with no
error shown, even though nothing was deleted server-side. On next reload the "removed" member
reappears with no explanation.
**Fix:** Chain `.select()` and check the returned array length, or re-fetch the roster after
delete instead of only trusting `error === null`:
```ts
const { data, error } = await supabase
  .from("workspace_members")
  .delete()
  .match({ workspace_id: workspaceId, user_id: removeTarget.user_id })
  .select();

if (error || !data || data.length === 0) {
  setRemoveError("멤버를 제거하지 못했습니다.");
  return;
}
```

### WR-04: `JobStepper` polls forever, even after every job reaches a terminal state

**File:** `apps/dashboard/components/JobStepper.tsx:73-98`
**Issue:** The polling `useEffect` calls `poll()` immediately and then
`setInterval(poll, POLL_INTERVAL_MS)` (3s), clearing the interval only on unmount. There is no
check for "all `STAGE_TYPES` jobs are in `TERMINAL_STATUSES`" to stop the interval early. Since
one `JobStepper` is mounted per row in `SourcesList` and rows persist on screen indefinitely
(no unmount once done), a workspace with many historical sources will keep firing
`GET /workspaces/{id}/sources/{id}/jobs` every 3 seconds per row, forever, for as long as the
Sources page stays open — long after the job chain has fully succeeded or dead-lettered and
nothing can change.
**Fix:** Once the fetched `jobs` show all `STAGE_TYPES` in a terminal status, stop scheduling
further polls (e.g. track a `settled` boolean and skip `setInterval`/clear it once reached).

### WR-05: Inconsistent / missing fail-fast validation for `NEXT_PUBLIC_*` env vars

**Files:**
- `apps/dashboard/lib/supabase/client.ts:14-16`
- `apps/dashboard/lib/supabase/server.ts:21-23`
- `apps/dashboard/middleware.ts:26-28`
- `apps/dashboard/lib/api-client.ts:80`
- `apps/dashboard/components/AskConversation.tsx:130`

**Issue:** `lib/supabase/client.ts`, `server.ts`, and `middleware.ts` read
`process.env.NEXT_PUBLIC_SUPABASE_URL!` / `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY!` with a
TypeScript non-null assertion that provides zero runtime protection — if the env var is
actually missing at runtime, `createBrowserClient`/`createServerClient` receive `undefined`
and throw whatever opaque error the Supabase SDK produces. `lib/api-client.ts` and
`AskConversation.tsx` interpolate `process.env.NEXT_PUBLIC_API_URL` directly into a template
string with no guard at all — if unset, requests silently go to a URL literally starting with
the string `"undefined/..."`. CLAUDE.md's documented project convention is explicit: *"Config
errors fail fast at boot: a missing environment variable must abort startup naming the
specific key."* None of these five call sites do that — a misconfigured deploy (missing env
var in Railway/Vercel) fails with a confusing downstream error instead of a clear
"NEXT_PUBLIC_SUPABASE_URL is not set" message.
**Fix:** Centralize env access behind a small helper that throws a named error at first use,
e.g.:
```ts
function requireEnv(name: string): string {
  const value = process.env[name];
  if (!value) throw new Error(`Missing required environment variable: ${name}`);
  return value;
}
```
and use it in place of the bare `process.env.X!` / unguarded interpolations.

## Info

### IN-01: `GraphLensFilter` declares an unused `workspaceId` prop

**File:** `apps/dashboard/components/GraphLensFilter.tsx:22-25`
**Issue:** `GraphLensFilterProps` requires `workspaceId`, and the component destructures it as
`workspaceId: _workspaceId` purely to silence the unused-var lint rule — the value is never
used anywhere in the component body. The caller (`app/w/[workspaceId]/graph/page.tsx:23-26`)
still passes it. Either the prop is dead weight that should be removed from the type/call site,
or it was meant to be used (e.g. for a workspace-scoped category-count fetch) and that part of
the implementation is missing.
**Fix:** Remove the prop from `GraphLensFilterProps` and its call site if it's truly unneeded,
or use it if a future requirement needs it.

### IN-02: Array-index React keys in dynamically re-split segment lists

**Files:** `apps/dashboard/components/AskConversation.tsx:387-402` (`renderSegments`),
`apps/dashboard/components/WikiPageContent.tsx:183-202` (`wikiLinkParts.map`)
**Issue:** Both loops use the array index as the React `key`. Because `splitTextWithAnchors`/
`resolveWikiLinks` fully recompute the parts array on every render (rather than diffing), this
is low-risk in practice, but it's still a discouraged pattern — if either helper is ever
changed to do incremental/partial updates, using index keys would cause citation markers/links
to be misattributed across re-renders instead of a hard failure, making a future regression
harder to spot.
**Fix:** Derive a stable key from content (e.g. `` `${part.type}-${i}-${'alias' in part ? part.alias : part.value.slice(0,8)}` ``) if these lists are ever made to update incrementally.

---

_Reviewed: 2026-08-12T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

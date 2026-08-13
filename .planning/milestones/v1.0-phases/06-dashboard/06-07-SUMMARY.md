---
phase: 06-dashboard
plan: 07
subsystem: ui
tags: [nextjs, react, typescript, supabase, vitest, wikilinks, rls]

# Dependency graph
requires:
  - phase: 06-dashboard (06-01)
    provides: "@supabase/ssr client factories, middleware.ts tenancy gate, /w/[workspaceId] RLS-scoped routing, NavShell '위키' link"
  - phase: 06-dashboard (06-04)
    provides: "apps/dashboard/lib/api-client.ts — apiFetch()/ApiError for the verify-status PATCH"
provides:
  - "apps/dashboard/lib/wiki-links.ts — baseSlug()/resolveWikiLinks(), a JS port of nexuswiki_core.slug._base_slug"
  - "apps/dashboard/components/WikiPageContent.tsx — read-only banner, disputed/verification callouts, verify action"
  - "apps/dashboard/components/RedLinkCta.tsx — unresolved-WikiLink CTA routing to source creation"
  - "apps/dashboard/app/w/[workspaceId]/wiki/[slug]/page.tsx and .../wiki/page.tsx — the wiki detail/index routes"
affects: []

# Actuals (#2632)
actuals:
  tokens: 7384
  tasks: 3
  commits: 5

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "TDD RED/GREEN for pure-function modules (wiki-links.ts), mirroring the citation-anchors.ts precedent from 06-06"
    - "Icon-only interactive touch targets get their own nested <button aria-label> separate from adjacent static copy text, so the accessible name stays exactly the required copy (RedLinkCta's 지금 생성 icon vs its visible 아직 작성되지 않음 · 지금 생성 label text)"
    - "Server-side role gating with an RPC-first/table-read-fallback pair (has_workspace_role RPC, then a direct workspace_members row read) — a UX-only convenience gate; the real write boundary stays in apps/api's own RLS-backed UPDATE policy"

key-files:
  created:
    - apps/dashboard/lib/wiki-links.ts
    - apps/dashboard/tests/wiki-links.test.ts
    - apps/dashboard/components/WikiPageContent.tsx
    - apps/dashboard/components/RedLinkCta.tsx
    - apps/dashboard/tests/RedLinkCta.test.tsx
    - "apps/dashboard/app/w/[workspaceId]/wiki/[slug]/page.tsx"
    - "apps/dashboard/app/w/[workspaceId]/wiki/page.tsx"
  modified:
    - apps/dashboard/package.json
    - apps/dashboard/pnpm-lock.yaml

key-decisions:
  - "baseSlug() ports only nexuswiki_core.slug._base_slug's collision-free transform, not slugify()'s taken-set collision-suffix resolution — a rare server-side `-2`-suffixed slug will render as an unresolved red link even though a matching page exists; documented as a safe-failure limitation (worst case: a redundant create-CTA on a working page), not a data-loss bug (06-07-PLAN.md assumptions)"
  - "normalize() approximates Python str.casefold() with JS toLowerCase() — the two diverge on some Unicode case-folding edge cases (e.g. German ß, Turkish dotless i); acceptable for this display-only path"
  - "resolveWikiLinks() always emits a computed slug for unresolved matches (even ones with zero corresponding wiki_links row) so RedLinkCta always has a slug-shaped identifier to work with, even before a link_sync job has run"
  - "'partial' verification_status gets the same warning-text treatment as an expired 'verified' status — UI-SPEC has no dedicated partial copy row; documented in-component as this component's own reasonable extension, not a UI-SPEC requirement"
  - "The disputed callout always renders before the body block regardless of verification_status — both in DOM order and in file/source order, per the plan's structural safety prohibition (T-06-22): a user must never be able to scroll past the disputed warning unseen"
  - "RedLinkCta builds its navigation URL with manual encodeURIComponent() string interpolation, exactly as the plan's <action> specifies — NOT URLSearchParams, which encodes spaces as `+` instead of `%20` and broke the plan's expected query-string shape (caught live during the RED/GREEN-adjacent test run, fixed before commit)"
  - "wiki/[slug]'s not-found branch ('페이지를 찾을 수 없습니다') is NOT treated as a D-12 no-enumeration case — the query is already scoped to the caller's own workspace_id, so distinguishing 'wrong slug' leaks nothing about other tenants"
  - "canVerify is resolved server-side via the has_workspace_role RPC first, falling back to a direct workspace_members row read (always permitted by RLS for one's own row) if the RPC is ever unavailable — this gate is UX convenience only; the actual write boundary is wiki.py's own RLS-backed UPDATE policy (T-06-21)"
  - "Live Playwright click-through verification (WikiLink navigation, all 4 verification callouts, disputed-priority, red-link CTA flow) was attempted twice against the local Supabase stack but both runs stalled/were interrupted by session limits; abandoned in favor of static-only verification (vitest/tsc/next build) rather than continuing to retry — recorded as an open gap (.planning/WINDOWS.md #12), not silently claimed as verified. All throwaway seed data (test user, workspace, 6 wiki_pages, 2 wiki_links) was cleaned up and confirmed at 0 rows remaining before abandoning the attempt"

patterns-established:
  - "Pure client-side ports of a Python core module (slug/tokenizer normalization) document their known divergence from the Python original inline, in the module's own header comment, rather than silently claiming byte-identical behavior"
  - "Icon-only touch targets (44×44px) get a dedicated <button aria-label> distinct from any adjacent visible label text — the accessible name is never diluted by surrounding copy"

requirements-completed: [UI-05]

coverage:
  - id: D1
    description: "baseSlug() mirrors nexuswiki_core.slug._base_slug for the common case (Korean, punctuated-English, and mixed titles), verified against real Python-computed fixture values; resolveWikiLinks() correctly splits [[제목]] WikiLink content into ordered text/link parts, matching resolved/unresolved wiki_links rows by computed slug"
    requirement: "UI-05"
    verification:
      - kind: unit
        ref: "apps/dashboard/tests/wiki-links.test.ts (9 tests: 4 baseSlug fixture cases incl. Python-verified values, 5 resolveWikiLinks cases incl. zero-match passthrough)"
        status: pass
    human_judgment: false
  - id: D2
    description: "RedLinkCta renders the verbatim copy '아직 작성되지 않음 · 지금 생성', exposes its create icon as a button with aria-label='지금 생성', and navigates to /w/[workspaceId]/sources?prefillTitle=<encoded title>&tab=text on click — never creates or edits a wiki_pages row directly"
    requirement: "UI-05"
    verification:
      - kind: unit
        ref: "apps/dashboard/tests/RedLinkCta.test.tsx (4 tests: copy+title render, aria-label button, correct prefillTitle/tab=text navigation, sources-path-only assertion)"
        status: pass
    human_judgment: false
  - id: D3
    description: "WikiPageContent has zero contentEditable surface and zero write path targeting wiki_pages content — the only mutation in the component tree is the verification-status PATCH"
    requirement: "UI-05"
    verification:
      - kind: other
        ref: "grep -c \"contentEditable\" WikiPageContent.tsx == 0; grep -c \"wiki_pages\" WikiPageContent.tsx == 0 (no literal reference at all, stricter than the plan's own acceptance grep)"
        status: pass
    human_judgment: false
  - id: D4
    description: "The disputed callout always precedes the body-rendering block in both file/source order and DOM order, regardless of verification_status — structural guarantee against scrolling past an unseen conflict warning"
    requirement: "UI-05"
    verification:
      - kind: other
        ref: "grep -n confirms the disputed-branch JSX (line 126) appears before wikiLinkParts.map (line 183) in WikiPageContent.tsx"
        status: pass
    human_judgment: false
  - id: D5
    description: "The read-only banner (verbatim copy), the four verification-status callouts (verified/expired/partial/unverified) with correct UI-SPEC colors, and the resolved/red WikiLink rendering inside a real page all render correctly at runtime"
    verification: []
    human_judgment: true
    rationale: "Not exercised by an automated render test (no WikiPageContent.test.tsx — the plan's own Task 2 <verify> was tsc-only) and not live-verified either: two Playwright click-through attempts against the local Supabase stack stalled/were interrupted before completing. The underlying logic units are proven (D1 wiki-links.ts, D2 RedLinkCta.tsx) and tsc/next build both pass clean, but the actual composed rendering was not observed running. Recorded as .planning/WINDOWS.md #12 (unrun-verify)."
  - id: D6
    description: "The wiki index route renders the empty-wiki copy ('아직 컴파일된 위키 페이지가 없습니다' / '소스를 추가하면 자동으로 위키 페이지가 생성됩니다.') when a workspace has zero wiki_pages rows, and a populated list of title links otherwise; the wiki/[slug] route renders '페이지를 찾을 수 없습니다' for a missing slug within the caller's own workspace"
    verification: []
    human_judgment: true
    rationale: "No automated test exists for either route (Server Components reading via RLS-scoped Supabase client — same untestable-under-jsdom class as every other Phase 6 RSC page in this codebase). next build generates both routes successfully and code review confirms the copy/branches match UI-SPEC verbatim, but neither state was exercised against real seeded data before the live-verification attempts were abandoned."
  - id: D7
    description: "canVerify correctly gates the '검증됨으로 표시' button to editor+ role, resolved server-side via has_workspace_role RPC with a workspace_members-row-read fallback"
    verification: []
    human_judgment: true
    rationale: "Not exercised against the real RLS-enabled local stack (the live-verification attempts that would have exercised this were interrupted). tsc/next build confirm the RPC call signature and fallback query compile correctly against the generated types, but the RPC's actual PostgREST-callable behavior was not observed at runtime this session."

# Metrics
duration: "~2h (including two interrupted live-verification attempts and cleanup)"
completed: 2026-08-12
status: complete
---

# Phase 6 Plan 7: Wiki Viewer (UI-05) Summary

**Read-only wiki viewer — `[[WikiLink]]` navigation with a client-side `_base_slug` port, four verification-status callouts, a disputed-conflict callout that always outranks them, and a red-link CTA that routes to source creation rather than any page-edit surface. This is the final plan of Phase 6 (8/8) — all six Phase 6 requirements (UI-01 through UI-06) are now delivered.**

## Performance

- **Duration:** ~2h (including two interrupted live-Playwright-verification attempts, seed/cleanup work, and a session-limit interruption)
- **Tasks:** 3/3 completed
- **Files created:** 7 (5 source, 2 test)
- **Files modified:** 2 (package.json/pnpm-lock.yaml — playwright devDependency)

## Accomplishments

- `lib/wiki-links.ts`: `baseSlug(title)` ports `nexuswiki_core.slug._base_slug` (NFKC normalize → hyphenate spaces → filter to `[0-9a-z가-힣-]` → collapse/trim hyphens → truncate 80 chars → deterministic fallback), verified against real Python-computed output for Korean/punctuated-English/mixed-language fixtures. `resolveWikiLinks(content, links)` scans `[[제목]]` WikiLink syntax and splits it into ordered text/link parts, matching each against the page's `wiki_links` rows by computed slug.
- `components/WikiPageContent.tsx`: renders the verbatim read-only banner, the disputed-conflict callout (always ranked above the body regardless of `verification_status`, per the plan's structural safety prohibition), one of four verification-status callouts (verified/expired/partial/unverified — colored per UI-SPEC), the Display-weight page title, an editor-gated "검증됨으로 표시" verify action wired to `apiFetch` PATCH, and the WikiLink-resolved body. Zero `contentEditable`, zero write path touching page content.
- `components/RedLinkCta.tsx`: renders the title (2-line clamp for long titles), the verbatim "아직 작성되지 않음 · 지금 생성" copy, and a 44×44px `aria-label="지금 생성"` icon button that navigates to `/sources?prefillTitle=<encoded>&tab=text` — never creates a `wiki_pages` row directly.
- `app/w/[workspaceId]/wiki/[slug]/page.tsx` and `.../wiki/page.tsx`: Server Components reading `wiki_pages`/`wiki_links` directly via the RLS-scoped Supabase client, matching the established `sources/page.tsx` pattern (no `apps/api` round trip for reads). The detail route resolves `canVerify` via `has_workspace_role` RPC with a `workspace_members`-row-read fallback and renders a same-tenant "페이지를 찾을 수 없습니다" state for a missing slug (not a D-12 no-enumeration case, since the lookup is already workspace-scoped). The index route renders the verbatim empty-wiki copy when a workspace has zero `wiki_pages` rows.
- Attempted full live-stack Playwright verification (throwaway user/workspace/6 wiki_pages covering all 4 statuses + disputed + a resolved/red WikiLink pair, seeded via GoTrue admin API + `docker exec -i psql`) twice; both attempts stalled/were interrupted before completing. All seed data was cleaned up and confirmed at 0 rows remaining. Abandoned live verification in favor of static-only checks (`vitest run`, `tsc --noEmit`, `next build`) rather than continuing to retry — the gap is recorded, not hidden (see Deviations and `.planning/WINDOWS.md` #12).

## Task Commits

Task 1 followed RED → GREEN (`tdd="true"`); Tasks 2 and 3 were each committed as a single `feat`:

1. **Task 1: lib/wiki-links.ts — slug port + link resolution**
   - `c3d460d` test(06-07): add failing test for wiki-links baseSlug/resolveWikiLinks (RED) — confirmed import-resolution failure before implementation existed
   - `e2301b0` feat(06-07): implement wiki-links.ts baseSlug/resolveWikiLinks (GREEN) — 9/9 tests pass
2. **Task 2: WikiPageContent.tsx** - `d6c1ddc` (feat)
3. **Task 3: RedLinkCta.tsx + wiki routes** - `92eadb5` (feat)

Additional (dev tooling, not a plan task): `20c0583` chore(06-07): add playwright devDependency for live UI verification tooling.

**Plan metadata:** _(this commit, follows below)_

## Files Created/Modified

- `apps/dashboard/lib/wiki-links.ts` - `baseSlug(title)`, `resolveWikiLinks(content, links)`, `WikiLinkPart` type
- `apps/dashboard/tests/wiki-links.test.ts` - Vitest, 9 tests (4 baseSlug fixtures incl. Python-verified values, 5 resolveWikiLinks cases)
- `apps/dashboard/components/WikiPageContent.tsx` - `WikiPageContent` component, `WikiPageContentProps` type
- `apps/dashboard/components/RedLinkCta.tsx` - `RedLinkCta` component, `RedLinkCtaProps` type
- `apps/dashboard/tests/RedLinkCta.test.tsx` - Vitest + Testing Library, 4 tests
- `apps/dashboard/app/w/[workspaceId]/wiki/[slug]/page.tsx` - route `/w/[workspaceId]/wiki/[slug]`
- `apps/dashboard/app/w/[workspaceId]/wiki/page.tsx` - route `/w/[workspaceId]/wiki` (index)
- `apps/dashboard/package.json`, `apps/dashboard/pnpm-lock.yaml` - `playwright` devDependency, added for the (ultimately interrupted) live verification pass; left installed as harmless dev tooling

## Decisions Made

See `key-decisions` in frontmatter for the full list. Summary: `baseSlug()`/`normalize()` are documented approximations of the Python originals (safe-failure, display-only); `resolveWikiLinks()` always returns a slug-shaped identifier even for unmatched links; the `partial` verification status reuses the expired-style warning treatment as a documented component extension; the disputed callout is structurally guaranteed to precede the body; `RedLinkCta`'s query string is built with manual `encodeURIComponent` (not `URLSearchParams`, which encodes spaces as `+`) exactly per the plan's `<action>`; `canVerify` uses an RPC-first/table-read-fallback pair server-side.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] RedLinkCta initially used URLSearchParams, which broke the plan's expected query-string shape**
- **Found during:** Task 3, running `tests/RedLinkCta.test.tsx` for the first time
- **Issue:** The first implementation built the navigation URL with `new URLSearchParams({...}).toString()`, which percent-encodes spaces as `+` rather than `%20`. The plan's `<action>` explicitly specifies `${encodeURIComponent(title)}` string interpolation, and the test (built directly from the plan's acceptance criteria) asserted the `%20`-shaped output, failing against the `URLSearchParams` output.
- **Fix:** Rewrote `handleCreate()` to interpolate `encodeURIComponent(title)` directly into the template string, matching the plan's `<action>` verbatim.
- **Files modified:** `apps/dashboard/components/RedLinkCta.tsx`
- **Verification:** `tests/RedLinkCta.test.tsx` 4/4 pass after the fix.
- **Committed in:** `92eadb5` (fixed before commit, no separate fix commit needed)

---

**Total deviations:** 1 auto-fixed (1 bug, caught before commit via its own test)
**Impact on plan:** No scope creep — the fix brought the implementation into exact alignment with the plan's own `<action>` text.

## Issues Encountered

- **Live Playwright verification against the local Supabase stack was attempted twice and both attempts were interrupted** — the first stalled inside a headless-shell browser install for the pinned Playwright version (revision not yet cached locally; resolved by explicitly installing `chromium@1234`), and after that install completed, a second run stalled for an extended period and was killed by a watchdog with no hung process left running. Rather than retrying a third time, live verification was abandoned in favor of static verification only (`vitest run`, `tsc --noEmit`, `next build`, plus targeted `grep`-based structural checks). This matches the precedent already set by `06-01`/`06-05`/`06-06`'s SUMMARYs, which documented equivalent "not live-verified this session" gaps as accepted `human_judgment: true` items rather than blocking on them.
- **All throwaway seed data was fully cleaned up despite the aborted verification** — a test user, one workspace, 6 `wiki_pages` rows (covering all 4 verification states + disputed + a resolved/red WikiLink pair), and 2 `wiki_links` rows were created via the GoTrue admin API and `docker exec -i psql`, then deleted (workspace cascade-deletes pages/links/membership; the auth user was deleted separately after the workspace no longer referenced it via `owner_id`). Confirmed 0 rows remaining for both the workspace and the auth user before moving on.
- Owner-membership deletion order matters when tearing down seed data: `protect_owner_membership` (0004) blocks deleting an owner's `workspace_members` row directly ("워크스페이스 소유자의 멤버십은 삭제할 수 없습니다") — deleting the parent `workspaces` row instead cascades correctly and avoids the trigger.

## User Setup Required

None - no external service configuration required. Verification used the already-running local Supabase stack (no cloud push, no new env vars).

## Next Phase Readiness

- **UI-05 is delivered: this completes all 6 Phase 6 requirements (UI-01 through UI-06). This was the last plan of Phase 6 (8/8 plans complete).**
- `NavShell`'s "위키" link now resolves to a real index page, and pages link through to real detail pages — all 5 of `NavShell`'s route links (소스/질문하기/위키/그래프/설정) now resolve, matching `06-08-SUMMARY.md`'s note that this was the one outstanding surface.
- **Blocker for future auditors:** D5/D6/D7 in this SUMMARY's `coverage` block are `human_judgment: true` with an honest "not live-verified" rationale — the read-only banner, all 4 verification callouts, disputed-priority rendering, WikiLink resolved/red navigation, the wiki index's empty/populated states, and `canVerify`'s RPC-based role gating were never exercised against the real running stack this session. `.planning/WINDOWS.md` #12 tracks this as an open `unrun-verify` item. A future session (or `/gsd-verify-work`) should seed representative wiki data and click through all of: unverified page (no callout), verified+unexpired (success callout), verified+expired (warning callout), partial (warning callout), disputed (disputed callout wins over verified), a resolved WikiLink navigation, and a red-link CTA click routing to `/sources?prefillTitle=...&tab=text`.
- The `playwright` devDependency (`apps/dashboard/package.json`/`pnpm-lock.yaml`) is left installed for whichever future session picks up that verification pass — it is dev-only tooling, not shipped to production.
- With all 6 Phase 6 requirements delivered, Phase 6 (dashboard) is ready for phase-level closeout (`/gsd-transition` or equivalent) — no further plans are queued under `06-dashboard`.

---
*Phase: 06-dashboard*
*Completed: 2026-08-12*

## Self-Check: PASSED

All 7 created files confirmed present on disk (`lib/wiki-links.ts`, `tests/wiki-links.test.ts`, `components/WikiPageContent.tsx`, `components/RedLinkCta.tsx`, `tests/RedLinkCta.test.tsx`, `app/w/[workspaceId]/wiki/[slug]/page.tsx`, `app/w/[workspaceId]/wiki/page.tsx`). All 5 commit hashes (`c3d460d`, `e2301b0`, `d6c1ddc`, `92eadb5`, `20c0583`) confirmed present in `git log --oneline`. Full Vitest suite (76/76), `tsc --noEmit` (clean), and `next build` (both wiki routes generated) re-confirmed clean before writing this summary. Throwaway live-verification seed data confirmed at 0 rows remaining in the local Supabase stack.

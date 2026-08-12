---
phase: 06-dashboard
plan: 08
subsystem: ui
tags: [nextjs, cytoscape, postgrest, supabase, vitest, graph]

requires:
  - phase: 06-dashboard
    provides: "06-01: @supabase/ssr client factories, middleware.ts tenancy gate, Tailwind 4 @theme tokens, /w/[workspaceId] RLS-scoped routing"
provides:
  - "GraphLensFilter.tsx — category lens filter chips (개념/엔티티/가이드/맵) driving ?category= URL search param"
  - "GraphCanvas.tsx — client-side Cytoscape knowledge-graph canvas fetching wiki_pages/wiki_links directly via PostgREST, with explicit visible 1000-row PostgREST cap handling"
  - "app/w/[workspaceId]/graph/page.tsx — /graph route, the last of the 5 NavShell links now resolving instead of 404ing"
affects: []

actuals:
  tokens: 4435
  tasks: 3
  commits: 2

tech-stack:
  added: []
  patterns:
    - "GraphCanvas.tsx fetches client-side (not the RSC page) so ?category= re-filtering re-triggers a fetch without a full navigation — the one Phase 6 surface that deliberately deviates from the project's otherwise-universal server-side-first-fetch convention"
    - "Cytoscape node color-by-category via selector-based stylesheet rules (node[category = \"x\"]) instead of a style-value mapper function — avoids @types-inferred function-signature friction and matches the standard cytoscape.js idiom"
    - "exact PostgREST count (returned alongside the page of rows via { count: \"exact\" }) is the primary 1000-row-cap signal, with nodes.length === 1000 as a fallback if the count header is ever unavailable — distinguishes 'exactly 1000 nodes total' from '1000+ nodes, capped'"

key-files:
  created:
    - apps/dashboard/components/GraphLensFilter.tsx
    - apps/dashboard/tests/GraphLensFilter.test.tsx
    - apps/dashboard/components/GraphCanvas.tsx
    - apps/dashboard/app/w/[workspaceId]/graph/page.tsx
  modified:
    - apps/dashboard/lib/api-client.ts

key-decisions:
  - "Direct wiki_pages/wiki_links PostgREST reads instead of the wiki_graph_neighborhood RPC — recorded and audited in Task 1 (no code change): the RPC requires a seed_wiki_id and caps at 200 rows (a different 'explore from one node' use case), while UI-06's literal requirement is a workspace-wide overview with explicit 1000-row-cap handling, which only makes sense against PostgREST's own max_rows=1000 ceiling"
  - "cose (force-directed) layout instead of breadthfirst — wiki_links is an arbitrary inter-page link graph (including cycles), not a hierarchy, so a root-assuming layout doesn't fit the data shape"
  - "4 category colors drawn from the palette's non-primary colors (--color-luxe #460479 for concepts, --color-plus #92174d for entities, --color-muted #6a6a6a for guides, --color-body #3f3f3f for maps) — --color-primary stays reserved for CTAs/active-step/citation-marker per UI-SPEC's Color section"
  - "GraphCanvas container uses an inline style ({ width: '100%', height: '640px' }) rather than a Tailwind max-w-*/w-*/h-* utility, per the known WINDOWS #11 Tailwind spacing-scale collision risk this phase has hit twice before (06-03)"

patterns-established:
  - "Selector-based Cytoscape stylesheet rules (node[attr = \"value\"]) for data-driven styling, reusable by any future graph/canvas feature"
  - "Client-fetch-in-component pattern for URL-search-param-driven re-filtering without a full page navigation"

requirements-completed: [UI-06]

coverage:
  - id: D1
    description: "GraphLensFilter renders 4 category chips (개념/엔티티/가이드/맵) with an implicit 'all' state; clicking a chip sets/clears the ?category= URL param, toggling the same chip again clears it back to 'all'"
    requirement: UI-06
    verification:
      - kind: unit
        ref: "apps/dashboard/tests/GraphLensFilter.test.tsx (4 tests: set param, clear on re-click, active/inactive aria-pressed+data-active, switch between categories)"
        status: pass
      - kind: manual_procedural
        ref: "Live Playwright pass against local supabase start: all 4 chip labels rendered, clicking 가이드 navigated to ?category=guides, clicking 맵 (empty result) rendered the exact empty-state copy"
        status: pass
    human_judgment: false
  - id: D2
    description: "GraphCanvas is built on direct wiki_pages/wiki_links PostgREST reads, not the wiki_graph_neighborhood RPC — Task 1's documented decision is actually followed in the shipped code, not just recorded in the plan"
    requirement: UI-06
    verification:
      - kind: other
        ref: "grep -c \"wiki_graph_neighborhood\" apps/dashboard/components/GraphCanvas.tsx returns 0 (including comments, not just code)"
        status: pass
    human_judgment: false
  - id: D3
    description: "The 1000-row PostgREST cap notice copy is present verbatim in GraphCanvas.tsx's source and is designed to render above the (still-shown, truncated) canvas when count > 1000 or a 1000-row page is returned — never a silent truncation"
    requirement: UI-06
    verification:
      - kind: other
        ref: "grep -F of the exact cap-notice string in components/GraphCanvas.tsx"
        status: pass
    human_judgment: true
    rationale: "Only the negative case (cap notice absent at n=4 nodes) was live-verified this session — no workspace with 1000+ wiki_pages exists to exercise the positive branch end-to-end. The count-based branch condition was verified by code review and the exact literal copy is grep-confirmed, but the actual >1000-row trigger path has not been exercised against real data."
  - id: D4
    description: "Clicking a node navigates to /w/[workspaceId]/wiki/[slug] using that node's slug"
    requirement: UI-06
    verification:
      - kind: manual_procedural
        ref: "Live Playwright pass: clicked into the rendered Cytoscape canvas (cose layout, non-deterministic node positions) against a throwaway workspace with 4 wiki_pages/2 wiki_links; landed on /w/{id}/wiki/entity-a after a node click. Throwaway account/workspace/pages/links deleted after (0 rows remaining, verified)."
        status: pass
    human_judgment: true
    rationale: "Cytoscape canvas rendering and click-to-navigate is not meaningfully unit-testable under jsdom (no canvas layout engine) — this plan relies on typecheck + build + manual/live verification for GraphCanvas.tsx, per the plan's own acceptance criteria."
  - id: D5
    description: "Zero nodes after the category filter renders the exact empty-state copy ('표시할 노드가 없습니다' / '카테고리 필터를 초기화하거나 다른 워크스페이스를 선택하세요.')"
    requirement: UI-06
    verification:
      - kind: manual_procedural
        ref: "Live Playwright pass: filtering to 'maps' (no seeded wiki_pages in that category) rendered both empty-state lines verbatim"
        status: pass
    human_judgment: true
    rationale: "Same class as D4 — live-stack verification only, no committed CI regression test for this client-fetch component."
  - id: D6
    description: "A centered spinner/skeleton renders before the Cytoscape layout settles (backstop truth, UI-SPEC loading/graph-canvas row)"
    requirement: UI-06
    verification: []
    human_judgment: true
    rationale: "Implemented (a centered spinning ring, shown while state.status === 'loading') but not asserted by an automated test or explicitly screenshotted mid-flight during the live verification pass (the local fetch resolved too fast to reliably capture the loading frame) — confirmed only by code review against the backstop's stated intent."

duration: ~2h (including live-stack seed/verify/cleanup and a pre-existing unrelated build-blocking type error found and fixed)
completed: 2026-08-12
status: complete
---

# Phase 6 Plan 8: Graph Canvas and Category Lens Filter Summary

**Cytoscape knowledge-graph canvas (`GraphCanvas.tsx`) built on direct `wiki_pages`/`wiki_links` PostgREST reads with an explicit, visible 1000-row-cap notice, plus a `GraphLensFilter.tsx` category chip filter driving the `?category=` URL param — UI-06 is now satisfied, completing all 6 Phase 6 requirements.**

## Performance

- **Duration:** ~2h (component implementation, tsc/build verification, a pre-existing unrelated type-error fix required to unblock the build, and a full live-stack Playwright verification pass with seed/cleanup)
- **Tasks:** 3/3 completed (Task 1 was documentation-only, no commit)
- **Files modified:** 5 (4 created, 1 modified)

## Accomplishments

- Recorded (Task 1, no code) the audited rationale for building the graph canvas on direct `wiki_pages`/`wiki_links` PostgREST reads instead of the `wiki_graph_neighborhood` RPC — the RPC serves a different "explore from one seed node" use case (200-row cap, requires `seed_wiki_id`), while UI-06's literal requirement is a workspace-wide overview with explicit 1000-row-cap handling.
- Built `GraphLensFilter.tsx`: 4 category chips (개념/엔티티/가이드/맵) reusing `wiki_pages.category`'s fixed CHECK values, with an implicit "all" state when no chip is active; clicking toggles the `?category=` URL search param via `useRouter().push`.
- Built `GraphCanvas.tsx`: client-side fetch of `wiki_pages` (nodes) and `wiki_links` (resolved edges only, `to_wiki_id IS NOT NULL`) scoped to the fetched node-id set, with an exact-count-based 1000-row-cap detector (falls back to `nodes.length === 1000` if the count header is ever unavailable), 4-color category styling via Cytoscape selector rules, a `cose` force-directed layout (documented rationale: `wiki_links` is an arbitrary link graph, not a hierarchy), and tap-to-navigate to `/w/[workspaceId]/wiki/[slug]`.
- Built `app/w/[workspaceId]/graph/page.tsx`: the last of NavShell's 5 route links to get a real page — resolves the async `searchParams.category`, renders `GraphLensFilter` above `GraphCanvas`.
- Found and fixed (Rule 3, blocking) a pre-existing type error in `lib/api-client.ts` (from `06-04-PLAN.md`, not this plan's own files) that broke `next build`'s type-check phase — a TypeScript 5.9 `lib.dom.d.ts` change made `Uint8Array` generic, which no longer structurally matches `BodyInit`. Narrowed with a single type assertion; no runtime behavior change.
- Ran a full live end-to-end verification against the real local Supabase stack: seeded a throwaway account + workspace + 4 `wiki_pages` (2 concepts, 1 entity, 1 guide) + 2 `wiki_links` via GoTrue admin API + `docker exec psql`, drove the running `next dev` server with a plain Playwright script (not a gstack-branded skill, per project constraint). Confirmed: all 4 chips render, category filter changes the URL and re-fetches, an empty category renders the exact empty-state copy, the cap notice is absent at n=4 (correct — no cap should trigger), a directed-edge graph renders with correct per-category node colors (screenshot captured), and clicking a node navigates to `/w/[id]/wiki/entity-a`. All throwaway data deleted and verified at 0 rows remaining afterward.

## Task Commits

Task 1 was documentation-only (audited in this SUMMARY and the plan itself — no code, no commit). Each remaining task was committed individually:

1. **Task 1: Design rationale — direct reads over the neighborhood RPC** — no commit (documentation-only, already recorded in `06-08-PLAN.md`/`COVERAGE.md`)
2. **Task 2: GraphLensFilter.tsx** - `94b98f7` (feat)
3. **Task 3: GraphCanvas.tsx + graph/page.tsx** (includes the scoped `lib/api-client.ts` blocking-fix) - `1b1cdbd` (feat)

**Plan metadata:** _(this commit, follows below)_

## Files Created/Modified

- `apps/dashboard/components/GraphLensFilter.tsx` - `GraphLensFilter` component, `GraphLensFilterProps` type
- `apps/dashboard/tests/GraphLensFilter.test.tsx` - Vitest + Testing Library, 4 tests
- `apps/dashboard/components/GraphCanvas.tsx` - `GraphCanvas` component, `GraphCanvasProps` type
- `apps/dashboard/app/w/[workspaceId]/graph/page.tsx` - `/graph` route
- `apps/dashboard/lib/api-client.ts` - Type-assertion fix for a pre-existing `Uint8Array`/`BodyInit` mismatch (unrelated to this plan's own scope, but blocking its `next build` verification step)

## Decisions Made

- Direct PostgREST reads over the `wiki_graph_neighborhood` RPC (Task 1, audited — see Deviations/Key Decisions above).
- `cose` layout over `breadthfirst` — no assumed root node fits `wiki_links`' arbitrary/cyclic link structure.
- 4 category colors from the palette's non-primary colors (`--color-luxe`/`--color-plus`/`--color-muted`/`--color-body`) — `--color-primary` stays reserved per UI-SPEC.
- Inline `style` (not a Tailwind `w-*`/`h-*`/`max-w-*` utility) for the Cytoscape mount container's dimensions, per the known WINDOWS #11 collision risk.
- `GraphCanvas.tsx` fetches client-side rather than in the RSC `page.tsx`, so `?category=` re-filtering re-triggers a fetch without a full page navigation — documented as a deliberate deviation from Phase 6's otherwise-universal server-first-fetch convention.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Pre-existing `lib/api-client.ts` type error blocking `next build`**
- **Found during:** Task 3, running the plan's own `<verify>` command (`tsc --noEmit && next build`)
- **Issue:** `tsc --noEmit` alone passed cleanly (misleadingly, due to a stale `tsconfig.tsbuildinfo` incremental-compile cache), but `next build`'s own type-check phase failed on `lib/api-client.ts:66` — `Type 'Uint8Array<ArrayBufferLike>' is not assignable to type 'BodyInit'`. This file is untouched by this plan (created in `06-04-PLAN.md`); the root cause is TypeScript 5.9's `lib.dom.d.ts` making `Uint8Array` generic, which no longer structurally satisfies the `BodyInit` union in this project's installed `@types/node`/TS combination.
- **Fix:** Added a single `as BodyInit` type assertion at the one call site (`body = init.body as BodyInit`), with an inline comment explaining the TS-version cause. No runtime behavior change — `fetch` already accepted `Uint8Array` bodies at runtime; this is purely a type-level fix.
- **Files modified:** `apps/dashboard/lib/api-client.ts`
- **Verification:** Cleared the stale `tsconfig.tsbuildinfo`, re-ran `tsc --noEmit` (clean) and `next build` (succeeds, `/w/[workspaceId]/graph` route generated at 137 kB). Full Vitest suite (39/39) still passes.
- **Committed in:** `1b1cdbd` (part of Task 3's commit)

**2. [Rule 1 - Bug] Literal `wiki_graph_neighborhood` string present in a GraphCanvas.tsx comment, violating Task 3's own acceptance criterion**
- **Found during:** Task 3, running the acceptance-criteria grep after implementation
- **Issue:** A code comment explaining the cap rationale referenced the RPC by its literal function name, making `grep -c "wiki_graph_neighborhood" GraphCanvas.tsx` return 1 instead of the required 0 — the acceptance criterion is explicitly designed to catch even a comment-only mention, not just code usage.
- **Fix:** Reworded the comment to describe the RPC generically ("단일 시드 이웃 탐색용 그래프 RPC") with a pointer to the PLAN.md Task 1 rationale, instead of naming it literally.
- **Files modified:** `apps/dashboard/components/GraphCanvas.tsx`
- **Verification:** `grep -c "wiki_graph_neighborhood" apps/dashboard/components/GraphCanvas.tsx` now returns 0; `tsc --noEmit` and `next build` re-confirmed clean after the edit.
- **Committed in:** `1b1cdbd` (part of Task 3's commit, fixed before commit)

---

**Total deviations:** 2 auto-fixed (1 blocking, 1 self-caught acceptance-criteria bug)
**Impact on plan:** Both were necessary for Task 3's own stated `<verify>`/acceptance criteria to be genuinely satisfiable. No scope creep — no functionality beyond this plan's stated UI-06 scope was added.

## Issues Encountered

- **`tsc --noEmit` gave a false-clean signal on the first run** due to a stale `tsconfig.tsbuildinfo` incremental-compile cache masking the pre-existing `lib/api-client.ts` error — only `next build`'s own (non-incremental) type-check phase caught it. Clearing the buildinfo file before re-running `tsc --noEmit` reproduced the same error, confirming it wasn't a `next build`-specific issue.
- **Playwright's `canvas` locator initially resolved to 3 stacked Cytoscape layer canvases** (`layer0-selectbox`, `layer1-drag`, `layer2-node`), causing a Playwright strict-mode violation on the first verification script attempt. Scoped to `.last()` (the node layer) for click targeting in the second attempt.
- **`cose` layout produces non-deterministic node positions**, so the node-click verification script tried multiple sample points across the canvas rather than one fixed coordinate — this is expected behavior for a force-directed layout, not a bug, but worth noting for anyone writing a future automated regression test against this canvas.
- **Local Supabase stack required `docker exec -i`** (not plain `docker exec`) for heredoc-piped SQL to actually reach `psql`'s stdin — the first two seed-data insert attempts silently produced no output because `-i` was omitted.

## User Setup Required

None — no external service configuration required. All verification used the existing local Supabase stack (already running); no cloud push performed.

## Next Phase Readiness

- UI-06 is fully satisfied: category-filterable Cytoscape canvas, explicit (never silent) 1000-row-cap handling, node-click navigation to the wiki viewer — this completes all 6 Phase 6 requirements (UI-01 through UI-06).
- `/w/[workspaceId]/graph` is now a real route; all 5 of `NavShell`'s links (소스/질문하기/위키/그래프/설정) resolve to real pages as of this plan (though `/wiki/[slug]` itself — 06-05/06-06/06-07 — was not part of this plan's scope and its own completion status should be checked separately before considering Phase 6 fully closed).
- **Blocker for future auditors:** D3 (the actual >1000-row cap trigger), D4 (node-click navigation), D5 (empty-state copy), and D6 (loading spinner) are all `human_judgment: true` — verified live against the local stack this session but with no committed automated regression test, matching every other Phase 6 plan's documented RSC/canvas testing limitation (`apps/dashboard/vitest.config.ts` notes Cytoscape/canvas is not meaningfully testable under jsdom).
- **Tracked defect reference:** `.planning/WINDOWS.md` #11 (Tailwind spacing-scale collision) was consulted and deliberately avoided in `GraphCanvas.tsx`'s container sizing — no new occurrence to log.

## Self-Check: PASSED

All 5 files listed in "Files Created/Modified" verified present on disk. Both commit hashes (`94b98f7`, `1b1cdbd`) verified present in `git log --oneline`. `next build` (route `/w/[workspaceId]/graph` generated, 137 kB) and `pnpm exec vitest run` (39/39 passing) both re-confirmed clean before writing this summary.

---
*Phase: 06-dashboard*
*Completed: 2026-08-12*

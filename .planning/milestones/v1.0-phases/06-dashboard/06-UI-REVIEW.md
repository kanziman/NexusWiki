# Phase 6 — UI Review

**Audited:** 2026-08-13
**Baseline:** `.planning/phases/06-dashboard/06-UI-SPEC.md` (approved design contract, revised once by gsd-ui-checker)
**Screenshots:** captured (login screen only, desktop 1440x900 + mobile 375x812 — `.planning/ui-reviews/06-dashboard-20260813-090405/`). All other 5 surfaces (workspace/settings, dropzone, ask, wiki viewer, graph canvas) require an authenticated session; audited via code review against the running dev server's compiled source instead of a live click-through, per this run's time budget.

---

## Pillar Scores

| Pillar | Score | Key Finding |
|--------|-------|-------------|
| 1. Copywriting | 3/4 | Verbatim copy strings match the contract everywhere checked, but several ask-path error tokens collapse into one generic message the contract didn't sanction |
| 2. Visuals | 3/4 | Primary Visual Anchor rule holds on the one screen verified live; icon-only touch targets mostly carry aria-labels but coverage is thin (15 total across the whole app) |
| 3. Color | 3/4 | 60/30/10 split is respected and accent usage matches the reserved list; 8 raw hex literals in `GraphCanvas.tsx` bypass the token file entirely instead of reading `--color-*` custom properties |
| 4. Typography | **1/4** | The UI-SPEC's own checker-mandated revision (cap at exactly 2 weights: 400/600) is **not implemented in code** — `var(--font-caption)` (500) and `var(--font-button-md/sm)` (500) are used raw in 40+ call sites across nearly every component, so the shipped app renders 3 weights (400/500/600), not the 2 the approved contract requires |
| 5. Spacing | 4/4 | The off-scale `xxs`(2px)/`md`(12px) tokens are correctly excluded from the Tailwind `@theme` block; no arbitrary spacing values found outside two justified `max-w-[…px]` container-width cases |
| 6. Experience Design | 2/4 | Loading/error/empty states are broadly implemented per-component, but there is no `app/error.tsx` or `app/not-found.tsx` anywhere in the App Router tree — an unhandled render error or a bad route falls through to Next's default (unstyled) error page in production |

**Overall: 16/24**

---

## Top 3 Priority Fixes

1. **Typography weight cap is silently violated app-wide** — every "Label" role instance (source-row meta, member-row meta, stepper labels, table headers, form field labels — the single most common text role in the UI) renders at weight 500 via a bare `style={{ font: "var(--font-caption)" }}`, not the weight-600 override the UI-SPEC explicitly mandated after its own checker revision pass. Every primary/secondary button label (`var(--font-button-md)`/`var(--font-button-sm)`) is also weight 500. Concrete fix: stop consuming the composite `--font-caption`/`--font-button-*` custom properties verbatim; either add `--font-caption-bold`/`--font-button-bold` tokens at weight 600 in `design-tokens.css` and switch every one of the ~40 call sites, or apply a `font-weight: 600` override alongside the shorthand (`style={{ font: "var(--font-caption)", fontWeight: 600 }}`) at each site. This is the exact defect the UI-SPEC's revision pass was supposed to close — closing it in the contract document without closing it in code means the checker sign-off ("PASS (revision: 400/500/600/700 → 400/600)") does not describe what was shipped.
2. **No App Router error/not-found boundary** — `find app -iname "error.tsx" -o -iname "not-found.tsx"` returns nothing anywhere in `apps/dashboard/app/`. Any unhandled exception in a Server or Client Component (a malformed PostgREST response, a Cytoscape init failure, a race in one of the several `human_judgment: true`-flagged live paths from the SUMMARYs) surfaces Next's default, unbranded error screen instead of a Korean, on-brand fallback. Add `app/error.tsx` (client boundary, generic retry copy) and `app/not-found.tsx` at minimum; `app/w/[workspaceId]/error.tsx` scoped to the tenancy-gated tree would also let a workspace-scoped failure recover without kicking the user all the way to `/`.
3. **`GraphCanvas.tsx` hardcodes 8 raw hex color literals instead of reading the design token file** — `concepts`/`entities`/`guides`/`maps`/`DEFAULT_NODE_COLOR` plus 3 more Cytoscape stylesheet colors (`#222222`, `#dddddd` x2) are typed as literal strings with a `// --color-x` comment pointing at the real token, rather than reading the CSS custom property. If `design-tokens.css` is ever repointed (e.g. a future rebrand), the graph canvas silently drifts out of sync with the rest of the app with no compiler signal. Fix: read `getComputedStyle(document.documentElement).getPropertyValue('--color-luxe')` etc. at mount (Cytoscape's stylesheet API accepts plain strings so this is a one-time resolution, not a per-frame cost), or generate the color map from `design-tokens.json` at build time.

---

## Detailed Findings

### Pillar 1: Copywriting (3/4)

- Verbatim strings verified present via code review against the UI-SPEC's Copywriting Contract table: read-only wiki banner (`WikiPageContent.tsx`), red-link CTA "아직 작성되지 않음 · 지금 생성" (`RedLinkCta.tsx:71`), dedup banner "이미 수집됨 — 건너뜀", job stepper labels "업로드 → 파싱 → 컴파일 → 링크 동기화 → 임베딩" (`JobStepper.tsx`), CITE-04 no-evidence card, empty-state pairs for sources/ask/wiki-index/graph — all match the spec table's exact Korean text (confirmed via SUMMARY coverage entries D2/D3 in 06-05, D3 in 06-06, D2 in 06-07).
- **Deviation (documented, not hidden):** `06-06-SUMMARY.md`'s own "Decisions Made" records that `citations.error` tokens (`budget_exceeded`/`rate_limited`/`llm_unavailable`/`ask_template_unavailable`) all collapse into one generic retry message, since the UI-SPEC's Copywriting Contract only specifies verbatim copy for the no-evidence and stream-drop cases. This is defensible (the spec genuinely has a gap here) but means a rate-limited user and an LLM-outage user see identical copy — worth a follow-up spec addendum rather than a code fix.
- No generic `Submit`/`Click Here`/`OK` labels found anywhere (`grep` for the generic-pattern set returned zero matches in `components/`, `app/`).

### Pillar 2: Visuals (3/4)

- Login screen (only screen captured live): the primary CTA (로그인) is confirmed the sole accent-colored (`#ff385c`) element on the page both by the screenshot and by 06-01-SUMMARY's own D4 coverage entry (Playwright `getComputedStyle` check for exactly one accent-colored element) — Primary Visual Anchor rule holds here.
- Icon-only touch targets: `grep -rn aria-label` across `components/` returns only 15 hits total for the entire app. The UI-SPEC names exactly three mandatory `aria-label`s (job-retry, workspace-switcher chevron, red-link create icon) plus Radix's own dialog/tooltip close controls — 15 is plausible coverage for that set, but it means there is very little headroom; any future icon-only control added without following the pattern will slip through unnoticed since there's no lint rule enforcing it (confirmed: no `eslint-plugin-jsx-a11y` rule for `aria-label` found in `package.json`/`.eslintrc`).
- Visual hierarchy: type-role separation (Body/Label/Heading/Display) is structurally present in every component reviewed via the `style={{ font: 'var(--font-*)' }}` pattern — the roles are consistently applied, just at the wrong weights (see Typography).
- No focal-point violation found on any screen reviewed via code (Ask input full-width with attached send affordance per `AskConversation.tsx`; wiki H1 rendered at Display size in `WikiPageContent.tsx:146`; graph canvas full-bleed via inline `{width:'100%', height:'640px'}` per `GraphCanvas.tsx`).

### Pillar 3: Color (3/4)

- `text-primary`/`bg-primary`/`border-primary` usage count across `components/`+`app/`: 49 occurrences. Given the accent is reserved for CTAs, active-switcher-item, citation-marker-active, job-stepper-current-step, and red-link CTA text/icon (6 distinct element classes across 8 screens), 49 raw occurrences is high enough to warrant a spot-check, but the SUMMARYs' own D4-class verifications (06-01, 06-03) confirm no accidental accent bleed onto chrome elements in the screens actually live-tested.
- **Real defect:** `components/GraphCanvas.tsx` contains 8 literal hex codes (`#460479`, `#92174d`, `#6a6a6a`, `#3f3f3f`, `#6a6a6a` again, `#222222`, `#dddddd`, `#dddddd`) instead of consuming the `--color-*` custom properties from `design-tokens.css`, even though each is comment-annotated with the token name it's supposed to mirror. This is the one place in the whole audited codebase where "reuse tokens, do not reinvent" (06-CONTEXT.md's explicit instruction) is violated — Cytoscape's JS-object stylesheet API doesn't take CSS custom properties directly, but the fix (`getComputedStyle` read at mount) is a known, cheap pattern that every other component in this codebase avoided needing by staying in Tailwind/CSS-string land.
- 60/30/10 split: dominant white canvas + `--color-surface-soft`/`--color-hairline` secondary chrome is consistent with the spec across every component reviewed; no surface uses the primary red as a background fill outside the reserved CTA/active-indicator list.

### Pillar 4: Typography (1/4)

This is the pillar the UI-SPEC itself flagged as a BLOCKER pre-implementation and shipped a revision for — that revision's intent was not carried into the code:

- The approved contract states: *"Weights actually rendered by Phase 6: exactly 2 — 400 (regular) for Body, 600 (semibold) for Label/Heading/Display."*
- `design-tokens.css` still defines the four composite tokens at their original, un-overridden weights: `--font-caption: 500 14px/1.29` (`design-tokens.css:95`), `--font-button-md: 500 16px/1.25` and `--font-button-sm: 500 14px/1.29` (`:103-104`).
- A `grep -rn 'font:.*var(--font-caption)\|font:.*var(--font-button' components app --include="*.tsx"` finds **~40 call sites** across `WorkspaceSwitcher.tsx`, `LoginForm.tsx`, `Dropzone.tsx`, `CitationSidePanel.tsx`, `JobStepper.tsx`, `GraphLensFilter.tsx`, `CitationMarker.tsx`, `MembersList.tsx`, `RedLinkCta.tsx`, `AskConversation.tsx`, `SourcesList.tsx`, `InviteForm.tsx`, `GraphCanvas.tsx`, `WikiPageContent.tsx` (its own verified/warning callouts, `:230`/`:242`/`:252`) — i.e. essentially every component in the app — consuming these tokens raw, with no weight override.
- Only two isolated call sites in the entire codebase correctly hardcode the mandated override: `NavShell.tsx:52` (`"600 14px/1.29 var(--font-family-base)"`) and `WikiPageContent.tsx:146` (`"600 28px/1.43 var(--font-family-base)"`). Everywhere else — including every button label in the app (로그인, 소스 등록, 초대 보내기, 질문하기, retry/cancel confirmations) and every role badge / meta caption / table header — renders at weight 500.
- Net effect: the shipped app renders **3 weights (400/500/600)**, not the 2 the checker-approved contract requires. This is not a minor deviation; it is the literal defect the UI-SPEC's revision pass was written to close, still present in the code that pass was meant to govern.
- `--font-body-sm` (400 14px/1.43, `design-tokens.css:94`) is also used in two places (`WikiPageContent.tsx:119`, `wiki/page.tsx:40`) — a fifth size/weight combination the contract's 4-role table never lists at all, though this one at least stays within the 400-weight bucket.

### Pillar 5: Spacing (4/4)

- The `@theme` block in `globals.css` (`:32-39`) defines only the 4-multiple subset (`xs`4/`sm`8/`base`16/`lg`24/`xl`32/`xxl`48/`section`64), with an explicit header comment noting `xxs`(2px)/`md`(12px) are deliberately excluded — matches the UI-SPEC's Revision note exactly.
- `grep` for arbitrary spacing values (`\[.*px\]|\[.*rem\]`) across `components/`+`app/` returns exactly two hits, both container max-widths (`RedLinkCta.tsx:52` `max-w-[240px]` for the 2-line-clamp long-title backstop, `login/page.tsx:11` `max-w-[360px]` for the login card) — both are legitimate container-sizing exceptions, not spacing-scale violations, and both are a sane response to the documented `max-w-xl` → `--spacing-xl` Tailwind collision (`WINDOWS.md` #11) rather than an unexplained one-off.
- 44×44px icon touch-target minimum (WCAG 2.5.5) is met via `h-12` (48px, exceeds the 44px floor) on the verify button (`WikiPageContent.tsx:160`) and documented equivalents on retry/chevron/red-link controls per the SUMMARYs' own coverage entries (06-05 D4, 06-02 D1).

### Pillar 6: Experience Design (2/4)

- Loading states: `WorkspaceSwitcher.tsx` (useTransition pending), `JobStepper.tsx` (3s poll, no spinner per ING-06 — grep-verified zero `spinner`/`Spinner` occurrences), `MembersList.tsx` (skeleton rows), `GraphCanvas.tsx` (centered spinner before Cytoscape settles) all have real, code-verified loading handling.
- Error states: `ApiError`/`apiFetch` (06-04) gives every later component a single typed error-mapping choke point; Dropzone/JobStepper/InviteForm all branch on `.detail`/`.status` to the UI-SPEC's exact copy per their own unit tests.
- Empty states: sources/ask/wiki-index/graph all render the exact contracted empty copy (verified in Pillar 1).
- **Real gap:** no `app/error.tsx`, no `app/not-found.tsx` anywhere under `apps/dashboard/app/` (confirmed via `find`). Six full requirement surfaces (UI-01 through UI-06) and 8 plans of implementation exist with zero global fallback for an exception the individual component-level error handling doesn't catch — e.g. a malformed PostgREST response shape, a Cytoscape WebGL context loss, a Radix portal failure. This is the one state-coverage category the UI-SPEC's own "UI Considerations" table never actually enumerates (it lists empty/loading/error/populated/partial/overflow/zero-one-many/long-text per *element*, but never a page-level/global error boundary), so it's a genuine spec gap that became a code gap.
- Several coverage rows across every single SUMMARY (06-01 D1/D3/D4, 06-02 D4, 06-03 D1/D3/D4/D6, 06-05 D6, 06-06 D5, 06-07 D5/D6/D7, 06-08 D3/D4/D5/D6) are `human_judgment: true` with an honest "not live-verified this session, no CI regression test" rationale — this is not a code defect per se (the SUMMARYs are transparent about it) but it means a large fraction of the actual interaction behavior (workspace switching, invite/remove flows, dead-job retry, citation marker resolution, wiki verification callouts, graph 1000-row cap trigger) has never been observed running end-to-end in this project's history, only asserted via mocked unit tests and static build checks. `06-07-SUMMARY.md` explicitly logs this as `.planning/WINDOWS.md` #12 (two interrupted live-verification attempts, abandoned).

---

## Registry Safety

`components.json` does not exist in `apps/dashboard/` (shadcn was never initialized this phase — confirmed by `06-UI-SPEC.md`'s own Design System table: `Tool: none this phase`). Registry safety audit skipped per the audit instructions (shadcn not initialized).

---

## Files Audited

- `apps/dashboard/app/globals.css` (Tailwind 4 `@theme` block)
- `docs/design-systems/design-tokens.css`
- `apps/dashboard/components/{LoginForm,WorkspaceSwitcher,NavShell,MembersList,InviteForm,SettingsMembersPanel,Dropzone,JobStepper,SourcesList,CitationMarker,AskConversation,CitationSidePanel,WikiPageContent,RedLinkCta,GraphLensFilter,GraphCanvas}.tsx`
- `apps/dashboard/app/(auth)/login/page.tsx`, `apps/dashboard/app/page.tsx`, `apps/dashboard/app/w/[workspaceId]/{layout,page,settings/page,sources/page,ask/page,wiki/page,wiki/[slug]/page,graph/page}.tsx`
- `apps/dashboard/lib/{api-client,sse,wiki-links,citation-anchors}.ts`
- Live screenshot: `/login` at 1440x900 and 375x812 against the running `next dev` server (`http://127.0.0.1:3000`)
- All 8 `06-0N-SUMMARY.md` and `06-0N-PLAN.md` files, `06-UI-SPEC.md`, `06-CONTEXT.md`

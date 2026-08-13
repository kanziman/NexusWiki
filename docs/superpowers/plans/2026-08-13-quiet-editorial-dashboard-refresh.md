# Quiet Editorial Dashboard Refresh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restyle the workspace shell and Sources page into a warm, quiet editorial interface while preserving ingestion, job, security, and navigation behavior.

**Architecture:** Keep existing server/client ownership unchanged. Add reusable visual primitives in `globals.css`; apply the shell geometry in the workspace layout, `NavShell`, and `WorkspaceSwitcher`; then restyle `SourcesList`, `Dropzone`, and `JobStepper` without changing their props, fetches, state transitions, or approved Korean copy.

**Tech Stack:** Next.js 15, React 19, TypeScript, Tailwind CSS 4, Radix UI, Lucide, Vitest, Testing Library.

---

## File Structure

- `.gitignore`: ignore local visual-brainstorm artifacts.
- `apps/dashboard/app/globals.css`: warm neutral, ink-action, input, and focus primitives.
- `apps/dashboard/app/w/[workspaceId]/layout.tsx`: constrained responsive application canvas.
- `apps/dashboard/components/NavShell.tsx`: wordmark/header/active navigation semantics.
- `apps/dashboard/components/WorkspaceSwitcher.tsx`: visual-only selector refresh.
- `apps/dashboard/tests/NavShell.test.tsx`: shell route and active-state coverage.
- `apps/dashboard/components/SourcesList.tsx`: page introduction and ruled source rows.
- `apps/dashboard/tests/SourcesList.test.tsx`: empty state, title accessibility, and metadata coverage.
- `apps/dashboard/components/Dropzone.tsx`: presentation-only source-entry refresh.
- `apps/dashboard/components/JobStepper.tsx`: compact row-level status presentation.
- `apps/dashboard/tests/Dropzone.test.tsx`, `apps/dashboard/tests/JobStepper.test.tsx`: accessibility regression coverage.

### Task 1: Establish safe visual primitives

**Files:**

- Modify: `.gitignore`
- Modify: `apps/dashboard/app/globals.css`

- [ ] **Step 1: Ignore the persisted local companion output**

Append `.superpowers/` to the local-tooling section of `.gitignore`.

- [ ] **Step 2: Add the warm editorial custom properties**

Add these declarations to the existing `:root` rule in `apps/dashboard/app/globals.css`, below the font-family override:

```css
--nw-canvas: #fcfcfa;
--nw-surface: #ffffff;
--nw-ink: #171717;
--nw-body: #4d4d49;
--nw-muted: #7a7a74;
--nw-rule: #e7e7e1;
--nw-rule-strong: #c9c9c1;
--nw-focus: #171717;
--nw-action: #171717;
--nw-action-hover: #363632;
--nw-danger: #a33b2b;
```

- [ ] **Step 3: Add reusable focus, action, and input classes**

Append these exact classes below the existing `body` rule, also changing that rule to set the canvas and ink:

```css
body { margin: 0; background: var(--nw-canvas); color: var(--nw-ink); }
.nw-focus-ring:focus-visible { outline: 2px solid var(--nw-focus); outline-offset: 3px; }
.nw-action { background: var(--nw-action); color: #fff; border: 1px solid var(--nw-action); border-radius: 6px; transition: background-color 150ms ease, border-color 150ms ease; }
.nw-action:hover:not(:disabled) { background: var(--nw-action-hover); border-color: var(--nw-action-hover); }
.nw-action:disabled { cursor: not-allowed; opacity: 0.42; }
.nw-input { border: 1px solid var(--nw-rule-strong); border-radius: 6px; background: var(--nw-surface); }
.nw-input:focus { border-color: var(--nw-ink); box-shadow: 0 0 0 2px color-mix(in srgb, var(--nw-ink) 12%, transparent); outline: none; }
```

- [ ] **Step 4: Validate the foundation**

Run: `git diff --check -- .gitignore apps/dashboard/app/globals.css`

Expected: exit `0`.

- [ ] **Step 5: Commit**

Run: `git add .gitignore apps/dashboard/app/globals.css && git commit -m "style(dashboard): add quiet editorial primitives"`

### Task 2: Rebuild the shared workspace shell

**Files:**

- Modify: `apps/dashboard/app/w/[workspaceId]/layout.tsx`
- Modify: `apps/dashboard/components/NavShell.tsx`
- Modify: `apps/dashboard/components/WorkspaceSwitcher.tsx`
- Create: `apps/dashboard/tests/NavShell.test.tsx`

- [ ] **Step 1: Write a failing active-navigation test**

Create `NavShell.test.tsx`. Mock `usePathname` to return `/w/ws-1/sources` and mock `WorkspaceSwitcher` as a button. Render `NavShell` and assert all five Korean route links exist. Assert Sources has `aria-current="page"` and `data-active="true"`; Settings has neither.

```tsx
expect(screen.getByRole("link", { name: "소스" })).toHaveAttribute("aria-current", "page");
expect(screen.getByRole("link", { name: "소스" })).toHaveAttribute("data-active", "true");
expect(screen.getByRole("link", { name: "설정" })).not.toHaveAttribute("aria-current");
```

- [ ] **Step 2: Confirm it fails before the change**

Run: `pnpm --dir apps/dashboard test -- NavShell.test.tsx`

Expected: FAIL because the current links lack `data-active`.

- [ ] **Step 3: Implement the responsive canvas**

Replace the outer layout markup with:

```tsx
<div className="min-h-screen bg-[var(--nw-canvas)] text-[var(--nw-ink)]">
  <NavShell workspaces={workspaces ?? []} currentWorkspaceId={workspaceId} />
  <main className="mx-auto w-full max-w-6xl px-base py-xl sm:px-xl sm:py-xxl">{children}</main>
</div>
```

- [ ] **Step 4: Implement the header and active route treatment**

In `NavShell`, retain the existing route array and path matching. Render a `Nexus` link to `base`, wrap all content in `mx-auto max-w-6xl`, and make the route navigation `overflow-x-auto` at narrow widths. Each route link must retain `aria-current` and add `data-active={isActive ? "true" : undefined}`. Use this class exactly:

```tsx
className="nw-focus-ring shrink-0 border-b-2 border-transparent px-sm py-sm text-sm font-semibold text-[var(--nw-muted)] data-[active=true]:border-[var(--nw-ink)] data-[active=true]:text-[var(--nw-ink)]"
```

The nav must have `aria-label="워크스페이스 탐색"`; the wordmark must have `nw-focus-ring`.

- [ ] **Step 5: Refresh the workspace selector presentation only**

In `WorkspaceSwitcher`, preserve every hook, handler, Radix element, `aria-label`, and `data-active` value. Change the trigger class to `nw-focus-ring flex h-9 max-w-64 min-w-0 items-center gap-xs border-0 bg-transparent px-0 text-[var(--nw-ink)]`; change menu content to a white surface with `border-[var(--nw-rule)]` and shadow `0 12px 28px rgba(0,0,0,0.08)`; add `nw-focus-ring` to each menu item. Do not alter `router.push(workspacePath(id))`.

- [ ] **Step 6: Run focused tests**

Run: `pnpm --dir apps/dashboard test -- NavShell.test.tsx WorkspaceSwitcher.test.tsx`

Expected: PASS.

- [ ] **Step 7: Commit**

Run: `git add apps/dashboard/app/w/[workspaceId]/layout.tsx apps/dashboard/components/NavShell.tsx apps/dashboard/components/WorkspaceSwitcher.tsx apps/dashboard/tests/NavShell.test.tsx && git commit -m "style(dashboard): refresh workspace shell"`

### Task 3: Turn Sources into a ruled editorial library

**Files:**

- Modify: `apps/dashboard/components/SourcesList.tsx`
- Create: `apps/dashboard/tests/SourcesList.test.tsx`

- [ ] **Step 1: Write failing presentation tests**

Mock `Dropzone` and `JobStepper`, then render an empty list and assert the existing Korean heading/body. Render one long-title source, and assert title and accessible fallback retain the full value plus the Korean date.

```tsx
const title = "A very long research source title that must remain available";
const sourceTitle = screen.getByText(title);
expect(sourceTitle).toHaveAttribute("title", title);
expect(sourceTitle).toHaveAttribute("aria-label", title);
expect(screen.getByText("2026년 8월 12일")).toBeInTheDocument();
```

- [ ] **Step 2: Confirm the test fails**

Run: `pnpm --dir apps/dashboard test -- SourcesList.test.tsx`

Expected: FAIL because source titles have neither `title` nor `aria-label`.

- [ ] **Step 3: Implement page framing and responsive ruled rows**

Wrap the existing dropzone and conditional body in `mx-auto w-full max-w-4xl flex flex-col gap-xxl`. Before `Dropzone`, render this exact page intro:

```tsx
<section className="max-w-2xl">
  <p className="mb-sm text-xs font-semibold tracking-[0.12em] text-[var(--nw-muted)]">KNOWLEDGE LIBRARY</p>
  <h1 className="text-4xl font-semibold tracking-[-0.055em] text-[var(--nw-ink)] sm:text-5xl">Sources</h1>
  <p className="mt-sm text-base leading-7 text-[var(--nw-body)]">생각의 근거가 되는 자료를 모으고, 연결하고, 다시 찾으세요.</p>
</section>
```

Keep empty-state strings exactly. For non-empty data, make the `<ul>` `border-y border-[var(--nw-rule)]`; each row is `border-b border-[var(--nw-rule)] py-lg last:border-b-0` with no rounded card background. Use a `sm:flex-row` heading so date can wrap under title on mobile. Replace the title span with:

```tsx
<span title={source.title} aria-label={source.title} className="min-w-0 flex-1 truncate text-base font-semibold tracking-[-0.02em] text-[var(--nw-ink)]">{source.title}</span>
```

- [ ] **Step 4: Run focused tests**

Run: `pnpm --dir apps/dashboard test -- SourcesList.test.tsx`

Expected: PASS.

- [ ] **Step 5: Commit**

Run: `git add apps/dashboard/components/SourcesList.tsx apps/dashboard/tests/SourcesList.test.tsx && git commit -m "style(dashboard): present sources as editorial library"`

### Task 4: Restyle ingestion and processing without changing behavior

**Files:**

- Modify: `apps/dashboard/components/Dropzone.tsx`
- Modify: `apps/dashboard/components/JobStepper.tsx`
- Modify: `apps/dashboard/tests/Dropzone.test.tsx`
- Modify: `apps/dashboard/tests/JobStepper.test.tsx`

- [ ] **Step 1: Add accessibility regression tests**

Add this `Dropzone` test:

```tsx
it("keeps the file chooser and submit action accessible", () => {
  render(<Dropzone workspaceId="ws-1" />);
  expect(screen.getByLabelText("파일 선택")).toHaveAttribute("type", "file");
  expect(screen.getByRole("button", { name: "소스 등록" })).toBeDisabled();
});
```

Extend the first `JobStepper` test with:

```tsx
expect(screen.getByRole("list")).toBeInTheDocument();
expect(screen.getAllByRole("listitem")).toHaveLength(5);
```

- [ ] **Step 2: Run regression tests before class-only work**

Run: `pnpm --dir apps/dashboard test -- Dropzone.test.tsx JobStepper.test.tsx`

Expected: PASS.

- [ ] **Step 3: Apply quiet entry-surface styling**

In `Dropzone`, change no state, label, ID, handler, endpoint, tab value, button text, or error text. Apply these class changes only: root uses `border border-[var(--nw-rule)] bg-[var(--nw-surface)] p-base sm:p-xl` without rounded card classes; tabs use an ink underline via `data-[state=active]:border-[var(--nw-ink)]`; inputs/textarea add `nw-input`; drag target uses `border-dashed border-[var(--nw-rule-strong)] bg-[var(--nw-canvas)]`; submit buttons use `nw-action nw-focus-ring`; error banner retains `role="alert"` and test ID, using `border-[var(--nw-danger)] bg-[#fff8f6] text-[var(--nw-danger)]`.

- [ ] **Step 4: Compact the stepper presentation**

In `JobStepper`, do not change stage types, polling, endpoints, retry/cancel handlers, dialog copy, or accessible button names. Make the outer wrapper `border-l border-[var(--nw-rule)] pl-base sm:pl-lg`, reduce the list gap to `gap-xs`, use ink rather than pink for the current dot/label, use subdued rule color for inactive dots, and add `nw-focus-ring` to the existing 44px retry/cancel controls. Keep success/error icon meaning and Radix dialog structure intact; only update dialog canvas/rule/action classes.

- [ ] **Step 5: Run focused tests**

Run: `pnpm --dir apps/dashboard test -- Dropzone.test.tsx JobStepper.test.tsx`

Expected: PASS.

- [ ] **Step 6: Commit**

Run: `git add apps/dashboard/components/Dropzone.tsx apps/dashboard/components/JobStepper.tsx apps/dashboard/tests/Dropzone.test.tsx apps/dashboard/tests/JobStepper.test.tsx && git commit -m "style(dashboard): refine source entry and processing states"`

### Task 5: Full verification

**Files:**

- Modify only files from Tasks 1–4 if a validation failure requires a minimal correction.

- [ ] **Step 1: Run static validation**

Run: `git diff --check && pnpm --dir apps/dashboard test && pnpm --dir apps/dashboard typecheck`

Expected: each command exits `0`; all dashboard Vitest files pass.

- [ ] **Step 2: Inspect two browser widths**

Run: `pnpm --dir apps/dashboard dev`

At desktop and `360x800` on a member-authorized Sources URL, verify: all five routes and the selector are reachable; no page-level horizontal overflow exists; source title truncation retains its full tooltip/accessible name; file/URL/text tabs and their labels remain usable; tabbing shows focus on nav, selector, tabs, fields, and actions; job rows and retry/cancel controls remain readable/tappable.

- [ ] **Step 3: Commit only validation-driven changes**

If validation changed code, run `git add apps/dashboard && git commit -m "fix(dashboard): polish editorial responsive layout"`. If no files changed, do not create an empty commit.

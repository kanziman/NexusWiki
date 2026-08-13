# Dropzone File Picker Accessibility Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the existing single-file Sources dropzone open its file picker through click, Enter, and Space while preserving drag-and-drop and raw-file upload behavior.

**Architecture:** The visible drop target becomes the native label for the existing screen-reader-only file input. Label activation supplies pointer behavior; `tabIndex={0}` and an Enter/Space-only key handler use an input ref for keyboard behavior. The existing input `onChange` remains the sole selection-state boundary.

**Tech Stack:** Next.js 15, React 19, TypeScript, Radix Tabs, Vitest, Testing Library, OpenSpec.

---

## File Structure

- Create: `openspec/changes/fix-dropzone-file-picker/proposal.md` — motivation and scope.
- Create: `openspec/changes/fix-dropzone-file-picker/specs/source-file-selection/spec.md` — observable picker-accessibility behavior.
- Create: `openspec/changes/fix-dropzone-file-picker/design.md` — native-label implementation decision.
- Create: `openspec/changes/fix-dropzone-file-picker/tasks.md` — tracked implementation and verification checklist.
- Modify: `apps/dashboard/components/Dropzone.tsx:260-291` — associate visible drop target with the file input.
- Modify: `apps/dashboard/tests/Dropzone.test.tsx` — route-level component interaction regressions.

### Task 1: Create and validate the tracked change

**Files:**
- Create: `openspec/changes/fix-dropzone-file-picker/proposal.md`
- Create: `openspec/changes/fix-dropzone-file-picker/specs/source-file-selection/spec.md`
- Create: `openspec/changes/fix-dropzone-file-picker/design.md`
- Create: `openspec/changes/fix-dropzone-file-picker/tasks.md`

- [ ] **Step 1: Create a High-priority Linear issue before implementation**

Create an issue titled `Restore Sources dropzone file picker activation` with this description:

```markdown
The Sources file dropzone accepts drag-and-drop but does not open the operating-system file picker when clicked. Restore native click and keyboard activation without changing upload APIs or adding multi-file support.

OpenSpec change: `openspec/changes/fix-dropzone-file-picker/`
```

- [ ] **Step 2: Use `openspec-propose` to create `fix-dropzone-file-picker`**

The proposal must exclude multiple files, batch endpoints, MIME-policy changes, and authorization changes. The spec must require click, Enter, Space, drag/drop preservation, and no duplicate picker activation.

- [ ] **Step 3: Validate planning artifacts before apply**

Run: `npx --yes @fission-ai/openspec@1.8.0 validate fix-dropzone-file-picker --strict`

Expected: `Change 'fix-dropzone-file-picker' is valid`.

### Task 2: Add regression tests before implementation

**Files:**
- Modify: `apps/dashboard/tests/Dropzone.test.tsx`

- [ ] **Step 1: Add a failing test for visible-target click activation**

Give the visible target `data-testid="file-dropzone"`, render the component, spy on the labelled file input's `click`, and assert one invocation after clicking the target.

```tsx
it("opens the file picker when the visible dropzone is clicked", async () => {
  const user = userEvent.setup();
  render(<Dropzone workspaceId="ws-1" />);
  const input = screen.getByLabelText("파일 선택");
  const click = vi.spyOn(input, "click");

  await user.click(screen.getByTestId("file-dropzone"));

  expect(click).toHaveBeenCalledTimes(1);
});
```

- [ ] **Step 2: Add a failing test for keyboard activation**

```tsx
it.each(["{Enter}", " "])("opens the file picker with %s", async (key) => {
  const user = userEvent.setup();
  render(<Dropzone workspaceId="ws-1" />);
  const input = screen.getByLabelText("파일 선택");
  const click = vi.spyOn(input, "click");

  screen.getByTestId("file-dropzone").focus();
  await user.keyboard(key);

  expect(click).toHaveBeenCalledTimes(1);
});
```

- [ ] **Step 3: Run the focused test to establish the current failure**

Run: `pnpm test -- tests/Dropzone.test.tsx`

Expected: the new activation assertions fail because the visible `<div>` is not associated with the input.

### Task 3: Implement native label activation

**Files:**
- Modify: `apps/dashboard/components/Dropzone.tsx:260-291`
- Test: `apps/dashboard/tests/Dropzone.test.tsx`

- [ ] **Step 1: Replace the visible `<div>` with the input's `<label>`**

```tsx
<label
  htmlFor={fileInputId}
  data-testid="file-dropzone"
  tabIndex={0}
  onKeyDown={(event) => {
    if (event.key !== "Enter" && event.key !== " ") return;
    event.preventDefault();
    fileInputRef.current?.click();
  }}
  onDragOver={(event) => event.preventDefault()}
  onDrop={(event) => {
    event.preventDefault();
    const file = event.dataTransfer.files?.[0];
    if (file) setSelectedFile(file);
  }}
  className="flex cursor-pointer flex-col items-center gap-xs border border-dashed border-[var(--nw-rule-strong)] bg-[var(--nw-canvas)] p-xl text-center"
>
  {/* existing icon and selected-file text */}
  <input
    ref={fileInputRef}
    id={fileInputId}
    type="file"
    onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)}
    className="sr-only"
  />
</label>
```

Add `const fileInputRef = useRef<HTMLInputElement>(null);` beside the existing ids and update the React import to include `useRef`. Remove the nested screen-reader-only label because the visible label now names the input. Keep the existing input id, drag handlers, and single-file selection semantics unchanged.

- [ ] **Step 2: Run the focused regression tests**

Run: `pnpm test -- tests/Dropzone.test.tsx`

Expected: all Dropzone tests pass, including click, keyboard, drag/drop, and raw-file submission coverage.

- [ ] **Step 3: Check the file for unintended multi-file behavior**

Run: `rg -n 'multiple|files\?\.\[|FormData' apps/dashboard/components/Dropzone.tsx`

Expected: no `multiple` attribute, only the existing first-file selection paths, and no `FormData` upload conversion.

### Task 4: Verify and finalize

**Files:**
- Modify: `openspec/changes/fix-dropzone-file-picker/tasks.md`

- [ ] **Step 1: Run dashboard verification**

Run: `pnpm test && pnpm typecheck && pnpm lint`

Expected: all commands exit 0.

- [ ] **Step 2: Run strict OpenSpec validation and complete tasks**

Run: `npx --yes @fission-ai/openspec@1.8.0 validate fix-dropzone-file-picker --strict`

Expected: `Change 'fix-dropzone-file-picker' is valid`.

- [ ] **Step 3: Sync the new capability spec and archive after explicit approval**

Use `openspec-sync-specs` to create `openspec/specs/source-file-selection/spec.md`, validate specs, and use `openspec-archive-change` only after all change tasks are checked.

- [ ] **Step 4: Commit the focused feature change**

Run: `git add apps/dashboard/components/Dropzone.tsx apps/dashboard/tests/Dropzone.test.tsx openspec && git commit -m "fix(web): restore dropzone file picker activation"`

Expected: the commit contains only the dropzone behavior, tests, and its OpenSpec artifacts.

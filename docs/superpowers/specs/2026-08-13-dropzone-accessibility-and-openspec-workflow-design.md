# Dropzone Accessibility and OpenSpec Workflow Design

## Scope

This work has two independent, bounded outcomes:

1. Restore native file-picker activation for the existing single-file Sources dropzone.
2. Establish a repository-level agent workflow for Linear and OpenSpec work.

Multiple-file upload remains a separate future change.

## Dropzone Design

The visible file drop target becomes a `<label>` associated with the existing hidden file input. This preserves the current upload API, drag-and-drop behavior, selected-file state, and title flow. Native label activation opens the file picker for pointer interaction. Because labels are not keyboard-focusable by default, the target also receives `tabIndex={0}` and an `onKeyDown` handler that opens the input only for `Enter` and `Space`, preventing the browser default for Space to avoid duplicate activation.

The input stays the single source for file selection. Tests will verify pointer activation, keyboard activation, and that the existing raw-file submission behavior remains unchanged.

## Agent Workflow Design

The root `AGENTS.md` will define the mandatory lifecycle for work that changes behavior:

1. Create or link a Linear issue before planning; include the OpenSpec path once it exists.
2. Create an OpenSpec proposal, produce its required artifacts, and run strict validation.
3. Start implementation only after an explicit apply request; complete tasks incrementally.
4. Verify relevant tests, type checks, lint, and strict OpenSpec validation before completion.
5. Sync delta specs to main specs before archive when a change has capability specs.
6. Archive completed changes and update the Linear issue status.

The guidance will also require reporting, rather than guessing, when a connector cannot perform an operation because it omits required identifiers such as a Linear workflow state UUID.

## Non-Goals

- No multiple-file upload, filename-derived titles, or batch API changes.
- No modification of source-ingestion authorization, MIME validation, or storage behavior.
- No claim that a Linear issue is complete when the connector did not confirm the status change.

## Verification

- Dropzone-focused regression tests fail before the interaction change and pass after it.
- Dashboard test suite, type check, and lint pass.
- The OpenSpec change validates strictly; its main spec is synced before archive.

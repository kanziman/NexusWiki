## Context

See `proposal.md` for motivation. The file input is screen-reader-only and already owns selected-file state and the raw-byte upload flow. The visible drag target is currently a non-focusable `div`, so it does not activate the input.

## Goals / Non-Goals

**Goals:**

- Keep one input as the source of file-selection state.
- Support pointer and keyboard activation without duplicate picker opening.
- Preserve drag/drop and all existing upload behavior.

**Non-Goals:**

- Multiple-file selection or batch submission.
- Changes to API contracts, MIME validation, RLS, or storage behavior.

## Decisions

- Use the visible target as the label for the existing input so pointer activation is native.
- Make the label focusable and handle only Enter and Space with an input ref. Prevent Space's default behavior and call the input once, avoiding duplicated activation.
- Keep the current `onChange` and `onDrop` paths as the only state updates.

## Risks / Trade-offs

- [A custom key handler can fire twice] → Test each activation path and prevent the Space default before invoking the input.
- [Visual changes can break drag/drop] → Retain the existing drag handlers and test selected-file behavior.

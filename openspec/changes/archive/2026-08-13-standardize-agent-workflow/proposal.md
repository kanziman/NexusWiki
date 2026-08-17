## Why

Recent work used Linear and OpenSpec successfully, but the repository has no root instruction that requires agents to follow the same lifecycle. A documented standard prevents implementation, verification, sync, and external-tracker steps from being skipped or guessed.

## What Changes

- Add a root `AGENTS.md` with the required Linear and OpenSpec lifecycle.
- Define verification, delta-spec sync, archive, and connector-limitation reporting expectations.
- Preserve project-specific instructions already held in `.claude/CLAUDE.md`.

## Capabilities

### New Capabilities

None — this is documentation-only workflow guidance.

### Modified Capabilities

None.

## Impact

- Affected code: root `AGENTS.md`.
- No application behavior, API, database, or dependency changes.

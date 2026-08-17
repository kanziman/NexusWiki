## Context

See `proposal.md` for motivation. The repository has OpenSpec skills and a Linear connector but no root `AGENTS.md`; agents therefore lack a shared lifecycle and can receive incomplete connector metadata.

## Goals / Non-Goals

**Goals:**

- Put a concise, repository-wide workflow contract at the root.
- Require evidence-based verification, delta-spec sync, and archiving.
- Define safe handling for connector limitations.

**Non-Goals:**

- Replace skill-specific instructions or `.claude/CLAUDE.md` project conventions.
- Automate Linear state transitions without a discoverable workflow-state ID.

## Decisions

- Use root `AGENTS.md` as the single entry-point document, linking agents to the appropriate OpenSpec workflow rather than duplicating command details.
- Require an explicit user request before apply and archive actions.
- Treat missing connector IDs as a reportable limitation, never as permission to guess or claim success.

## Risks / Trade-offs

- [Instructions become stale] → Keep them lifecycle-focused and defer command semantics to the installed skills.
- [Linear connector capability differs by session] → Require verification from the connector response before reporting an external update.

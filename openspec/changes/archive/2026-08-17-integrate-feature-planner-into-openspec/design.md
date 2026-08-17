## Context

See `proposal.md` for motivation. OpenSpec 1.8.0 already supplies the desired `proposal → specs → design → tasks` graph. The project has parallel Codex skill and Claude command entrypoints for propose, a root `AGENTS.md` that mandates Linear, and an existing GitHub repository plus user Project #1 with `Todo`, `In Progress`, `Done`, parent issue, and sub-issue progress fields.

## Goals / Non-Goals

**Goals:**

- Preserve the existing `openspec-propose` name, schema, and artifact paths.
- Make one project-owned contract authoritative for both Codex and Claude.
- Enforce progressive planning gates without duplicating product planning documents.
- Make GitHub issue and Project state transitions verifiable and recoverable.

**Non-Goals:**

- Rewrite historical archived changes that mention Linear.
- Rename the existing GitHub Project or create new custom fields.
- Force three architecture options for mechanical changes.
- Change product runtime behavior.

## Decisions

### Keep the standard OpenSpec schema and enrich its project rules

`openspec/config.yaml` will add rules for proposal, specs, design, and tasks, while the existing artifact IDs and templates remain intact. The project-local propose skill will orchestrate progressive creation and approval instead of the package default's one-shot loop.

Alternatives considered:

- Fork a new `feature-planning` schema: rejected because it creates a second workflow identity and forces callers to choose a schema even though the artifacts are unchanged.
- Restore `spec-fixed.md`, `prd.md`, and `issues.md`: rejected because they duplicate OpenSpec and create synchronization ambiguity.

### Use the tracked project skill as the canonical cross-agent workflow

The canonical instructions will live at `.agents/skills/openspec-propose/SKILL.md`; `.gitignore` will track only that project-owned skill under the otherwise ignored generated `.agents/` tree. Claude's existing `.claude/commands/opsx/propose.md` becomes a thin adapter that requires the canonical skill. `.claude/CLAUDE.md` will explicitly require the root `AGENTS.md`, so tracker lifecycle rules are shared beyond the propose command.

Alternatives considered:

- Maintain two full copies: rejected because generated command and skill text would drift.
- Add a second `feature-plan` command: rejected because the user wants to retain the existing propose entrypoint.

### Use GitHub parent/sub-issues and Project #1

Create or reuse an umbrella issue before the OpenSpec change, then create approved task slices with `gh issue create --parent`. Add returned issue URLs to Project #1 and resolve the Status field and option IDs from `gh project field-list`; never hardcode or guess workflow identifiers. `tasks.md` remains the apply checklist and carries the corresponding issue URL.

Alternatives considered:

- One issue per change only: rejected because it loses the requested vertical-slice tracking.
- Flat issues: rejected because GitHub supports native parent/sub-issue progress and the existing Project exposes it.

### Preserve planning/apply authorization while honoring continuous progress

An ordinary propose request still stops after planning and requires explicit apply authorization. A request that already explicitly authorizes both planning and implementation may carry through the lifecycle under `AGENTS.md`; it passes only non-material gates automatically. Material ambiguity and failed validation remain hard stops.

## Risks / Trade-offs

- [OpenSpec regeneration can overwrite generated integrations] → Track the canonical project skill explicitly and keep the Claude adapter small enough to audit after regeneration.
- [GitHub Project field IDs can change] → Discover them per operation and verify the response rather than committing UUIDs to instructions.
- [Issue state and `tasks.md` can drift] → Require issue URLs in tasks, close only after the same task's fresh verification, and verify final GitHub state before reporting completion.
- [Four gates can slow small changes] → Permit zero-question requirement capture, proportional architecture analysis, and continuous authorization for non-material decisions.

## Migration Plan

1. Add artifact rules and shared workflow instructions while preserving the existing schema.
2. Replace Linear lifecycle text with GitHub issue/Project behavior and point Claude at `AGENTS.md`.
3. Baseline-test the old workflow, forward-test the enhanced Codex and Claude entrypoints, and run strict OpenSpec validation.
4. Sync the delta specs, archive this change, then mark GitHub issue #4 complete.

Rollback consists of restoring the previous propose skill/command, config rules, and `AGENTS.md`; GitHub issues already created remain auditable history.

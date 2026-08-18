---
description: 기능 아이디어를 4개 승인 게이트로 검증 가능한 OpenSpec 산출물과 GitHub 작업 항목으로 확정합니다.
argument-hint: "[change-name | feature description]"
---

# Plan Feature

Turn a feature idea into approved OpenSpec planning artifacts and linked GitHub work items, one approval gate at a time.

## Contract

The binding contract is `openspec/specs/feature-planning-workflow/spec.md`. Read it before starting.

This command is the Claude Code entrypoint for that contract. It owns the gates, the questioning discipline, and GitHub tracking. It does **not** restate the contract's rules and must not drift from them — if a rule needs to change, change the spec through an OpenSpec change, not this file.

Related contracts:

- Continuous authorization and pause exceptions: `openspec/specs/autonomous-workflow/spec.md`, mirrored in `.claude/CLAUDE.md` 「연속 진행 권한」.
- Artifact mechanics (creating and revising `proposal.md`, delta specs, `design.md`, `tasks.md`): delegate to `/opsx:propose` and `/opsx:update`. This command never hand-writes artifact formats.

## Input contract

Treat the raw command argument as `$ARGUMENTS`.

- Empty: ask which feature to plan. Never guess.
- A kebab-case name matching an active change under `openspec/changes/`: resume that change at its first incomplete gate. Determine position with `openspec status --change "<name>" --json`.
- Anything else: treat it as a feature description, derive a kebab-case change name, and confirm the name at Gate 1.

## Non-negotiable rules

- Investigate discoverable repository facts **before** asking anything. Never ask what the code, specs, or git history already answer.
- Ask at most **one** unresolved material question at a time, and always include a recommended answer with its rationale.
- A question is material only when different answers would change the resulting contract — user flow, boundary behavior, or terminology. Decide non-material details yourself and state the decision instead of asking.
- Never create `spec-fixed.md`, `prd.md`, `issues.md`, or any other parallel source of truth. The four OpenSpec artifacts are the only planning record.
- Never invent GitHub identifiers. Confirm every issue and Project mutation from command output before reporting it.
- Stop at each gate and wait for approval, unless continuous authorization applies.
- Planning ends at Gate 4. Implementation requires a separate explicit request via `/opsx:apply`.

## Gates

### Gate 1 — Requirements and terminology

1. Investigate the repository: existing specs under `openspec/specs/`, related archived changes, and the code the feature would touch.
2. Resolve material ambiguity in user flow, boundary behavior, and terminology — one question at a time, each with a recommendation.
3. Create or confirm the **GitHub umbrella issue** for this change. If none matches, create one, create the OpenSpec change with `openspec new change "<name>"`, link the change path in the issue body, and confirm both from command output.
4. Produce `proposal.md` and the delta spec requirements via `/opsx:propose`. Fixed requirements and ubiquitous language belong here — not in `design.md`.

**Gate**: present the proposal and requirement list, then wait.

### Gate 2 — Material architecture choice

Decide first whether a material architecture choice exists — two or more viable approaches that would materially change data, interfaces, dependencies, or task decomposition.

- **If it exists**: compare exactly three meaningful alternatives across the fixed criteria — data structure, API impact, state management, core behavior, component structure, existing-pattern consistency, testability. Present the comparison and a recommendation.
- **If it does not**: record the selected approach and any relevant rejected option with a concise rationale. Do not manufacture artificial alternatives.

**Gate**: present the comparison or the rationale, then wait.

### Gate 3 — Final design and non-goals

1. Record the selected ADR decision and its rejected options in `design.md`.
2. State non-goals explicitly. Anything deferred must appear here, not be left implied.

**Gate**: present `design.md`, then wait.

### Gate 4 — Vertical task breakdown

1. Break the work into dependency-ordered **vertical slices**. Each slice must produce independently verifiable behavior and normally fit within half a day to one day.
2. Never split slices by technical layer. A user-visible behavior spanning persistence, API, and UI is one slice, not three.
3. Give every slice Given-When-Then acceptance criteria and a verification command line.

**Gate**: present the slice list, then wait.

On approval:

4. Create one **GitHub sub-issue per slice** under the umbrella issue.
5. Add the umbrella and every sub-issue to `kanziman` Project #1 with status `Todo`.
6. Record the returned issue URLs in `tasks.md` next to their slices.
7. If GitHub or Project metadata is unavailable, or a command does not confirm success, do not guess identifiers and do not report the external transition as complete. Report the verified partial state.

## Completion

1. Run `openspec validate "<name>" --strict` and report the result.
2. Report the change path, umbrella issue URL, and each sub-issue URL.
3. State explicitly that implementation has not started and requires `/opsx:apply`.

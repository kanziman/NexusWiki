# Agent Workflow Standardization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a root `AGENTS.md` that makes Linear and OpenSpec lifecycle requirements consistent for repository changes.

**Architecture:** A concise repository-level instruction file owns the workflow contract. It directs agents to create a Linear issue, plan and validate an OpenSpec change, apply only with explicit user approval, verify before completion, sync specs, archive, and then update Linear.

**Tech Stack:** Markdown, Linear MCP, OpenSpec CLI.

---

## File Structure

- Create: `AGENTS.md` — repository-wide agent instructions and mandatory lifecycle.
- Reference: `.agents/skills/openspec-*/SKILL.md` — installed workflows agents must invoke rather than reproduce.

### Task 1: Add the repository workflow contract

**Files:**
- Create: `AGENTS.md`

- [ ] **Step 1: Create `AGENTS.md` with the complete workflow contract**

```markdown
# NexusWiki Agent Workflow

## Scope and safety

- Preserve unrelated working-tree changes.
- Use `apply_patch` for repository edits.
- Keep one user-approved behavior change per OpenSpec change unless the user explicitly groups work.

## Required lifecycle for behavior changes

1. Create or identify the Linear issue before implementation. Put the OpenSpec change path in its description once the change exists.
2. Use `openspec-propose` to create all required planning artifacts. Run `openspec validate <change> --strict` before requesting implementation.
3. Implement only after the user explicitly asks to apply the change. Use `openspec-apply-change`, work task-by-task, and update checkboxes immediately after each verified task.
4. Before marking a task or change complete, run the relevant tests, type checks, lint, and strict OpenSpec validation. Report failed checks accurately; do not mark their task complete.
5. For changes with delta specs, use `openspec-sync-specs` to merge them into `openspec/specs/` and validate specs before archiving.
6. Archive only completed changes with `openspec-archive-change`.
7. Update the Linear issue to its completed workflow state after archive.

## Connector limitations

- Never guess connector-only identifiers. If Linear requires a workflow state UUID that the available MCP tools cannot discover, leave the issue unchanged and report the limitation and the required follow-up.
- Do not claim an external status update succeeded without the connector response confirming it.

## Documentation-only and tooling changes

- Use an OpenSpec change when the work affects the development workflow or verification contract.
- For pure documentation edits outside that contract, confirm scope with the user and run only relevant validation.
```

- [ ] **Step 2: Verify the instruction file is complete and internally consistent**

Run: `rg -n 'TODO|TBD|<[^>]+>' AGENTS.md`

Expected: no output.

- [ ] **Step 3: Review the staged diff and commit the workflow standard**

Run: `git diff --check -- AGENTS.md && git diff -- AGENTS.md`

Expected: no whitespace errors; the diff only creates `AGENTS.md`.

Run: `git add AGENTS.md && git commit -m "docs: standardize Linear and OpenSpec workflow"`

Expected: a commit containing only the workflow contract.

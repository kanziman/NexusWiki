## Context

See `proposal.md` for motivation and `specs/pull-request-workflow/spec.md` for the observable contract. The repository already exposes project workflows as canonical skills under `.agents/skills/` and Claude Code commands as thin adapters. The working tree may contain large unrelated edits, so ordinary blanket staging is unsafe.

## Goals / Non-Goals

**Goals:**

- Keep one canonical, agent-readable PR workflow shared across clients.
- Preserve the source skill's issue-number ergonomics through `$ARGUMENTS` while accepting equivalent `#number` and issue URL forms.
- Make the mutation boundary reviewable before stage, commit, push, or GitHub writes.
- Make partial completion observable when a later external operation fails.

**Non-Goals:**

- Merging, auto-merging, force-pushing, amending, rebasing, or cleaning the worktree.
- Automatically deciding that all dirty files belong to the current change.
- Replacing OpenSpec apply, sync, archive, or GitHub issue lifecycle workflows.
- Encoding NexusWiki's current branch name or a fixed default branch.

## Decisions

### Canonical skill with a thin Claude adapter

**Context:** Multiple agents need the same safety behavior, while Claude slash commands provide `$ARGUMENTS` directly.

**Decision:** Put the complete workflow in `.agents/skills/create-pr/SKILL.md`. Add `.claude/commands/create-pr.md` that reads the canonical file and passes `$ARGUMENTS` unchanged.

**Alternatives:** Copy the full workflow into both locations; this was rejected because the copies would drift. Depend on a global personal skill; this was rejected because the project contract would not travel with the repository.

**Consequences:** The canonical directory must be explicitly unignored and the adapter must fail clearly if it is missing.

### Read-only planning followed by one approval gate

**Context:** Repository inspection and validation are safe to run before approval, but staging and GitHub writes alter state.

**Decision:** Resolve repository metadata, issue, change scope, diff, existing index, existing PR, validation plan, and draft metadata first. Present one complete mutation plan for approval. Treat staging as the first mutation.

**Alternatives:** Ask approval independently at every command; rejected as unnecessarily interruptive after the full plan is fixed. Mutate and then show the result; rejected because rollback could disturb unrelated work.

**Consequences:** Any material change to scope or PR metadata after approval requires a refreshed draft and approval.

### Explicit staging with an index collision guard

**Context:** `git add -A` and equivalent blanket operations can absorb unrelated deletions or edits. Resetting the index to recover would also modify user-owned state.

**Decision:** Compare the approved manifest with `git diff --cached`, block on unapproved pre-staged content, and use path-limited staging or controlled patch staging. Re-check the staged diff before commit.

**Alternatives:** Temporarily stash or reset unrelated changes; rejected because both mutate user-owned state. Use a temporary index; not chosen because it adds operational complexity and can surprise hooks that inspect the normal index.

**Consequences:** Mixed-scope files sometimes require user-assisted hunk selection or a separate commit.

### Discover remote state instead of assuming it

**Context:** Default branches, remotes, issue identities, and open PRs can differ by checkout.

**Decision:** Discover the current repository and default branch through `gh`, validate supplied issues in that repository, and query open PRs by head branch. Create a new PR only when none exists.

**Alternatives:** Hard-code `main` and `origin`; rejected because forks and future repository configuration can differ.

**Consequences:** Missing authentication, ambiguous remotes, or a detached/default branch blocks publication with a concrete diagnostic.

## Risks / Trade-offs

- [Agent judgment may select an incomplete manifest] → Show the complete diff-derived manifest and require explicit user approval; re-check the staged diff before commit.
- [Validation selection may miss a relevant check] → Read project instructions and manifests, include OpenSpec strict validation when OpenSpec files are in scope, and expose the exact plan before approval.
- [Push succeeds but PR creation or issue comment fails] → Report commit, remote branch, and PR/comment states separately so retry is safe.
- [Existing PR metadata differs from the approved draft] → Reuse the PR and update only metadata explicitly included in the approved plan.

## Migration Plan

1. Add the canonical skill and Claude adapter without changing existing git history.
2. Register the skill in project discovery docs and `.gitignore`.
3. Run skill validation and read-only RED/GREEN scenario tests.
4. Sync the new capability spec and archive the OpenSpec change.

Rollback removes the new skill, adapter, discovery entries, and capability spec; it does not require rewriting commits or PRs.

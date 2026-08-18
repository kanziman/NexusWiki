---
description: 승인된 변경만 안전하게 commit하고 GitHub PR을 생성하거나 갱신합니다.
argument-hint: "[issue-number | #issue-number | issue-url]"
---

# Create PR

Safely turn one approved unit of work into a verified commit and GitHub pull request. Preserve every unrelated worktree and index change.

## Input contract

Treat the raw command argument as `$ARGUMENTS`.

- Empty: proceed without an issue closing keyword. Never infer or invent an issue.
- `123`: resolve issue `#123`.
- `#123`: resolve issue `#123`.
- `https://github.com/<owner>/<repo>/issues/123`: accept only when `<owner>/<repo>` is the current `origin` GitHub repository.
- Anything else, multiple values, a PR URL, or an issue from another repository: stop before mutation and report the accepted forms.

Trim surrounding whitespace but otherwise do not reinterpret the input. Resolve `origin` with `git remote get-url origin`, normalize supported GitHub SSH and HTTPS forms to `<owner>/<repo>` by removing the transport, host prefix, and optional `.git` suffix, and reject a non-GitHub or ambiguous URL. Bind GitHub reads to that repository with `gh repo view <owner>/<repo>` and `gh issue view <number> --repo <owner>/<repo>`. Compare owner and repository names case-insensitively after normalization. Do not require the issue to be open, but show its state in the draft.

When an issue resolves, include a standalone `Closes #<number>` line in the proposed PR body. When no argument is supplied, omit the line and do not post an issue comment.

## Non-negotiable safety rules

- Read `AGENTS.md`, `.claude/CLAUDE.md`, relevant OpenSpec artifacts, and package manifests before drafting commands.
- Treat inspection and validation as read-only. Treat staging as the first repository mutation.
- Never use `git add -A`, `git add .`, an unbounded pathspec, `git commit -a`, `git stash`, `git reset`, or index cleanup to manufacture a clean state.
- Never amend, rebase, force-push, merge, enable auto-merge, delete branches, or close issues as part of this skill.
- Never include a path or hunk merely because it is dirty, related by directory, or already staged.
- Never overwrite or revert unrelated user changes.
- Do not create a commit if a required fresh validation fails.
- Verify every mutation from command output and a follow-up read before claiming it succeeded.

If completion requires a forbidden operation, stop and ask for separate direction.

## Workflow

### 1. Snapshot repository and remote state

Before changing anything, collect:

```bash
git status --short
git diff --name-status
git diff --cached --name-status
git branch --show-current
git rev-parse HEAD
git remote get-url origin
gh repo view "<origin-owner>/<origin-repo>" --json nameWithOwner,defaultBranchRef
gh pr list --repo "<origin-owner>/<origin-repo>" --head "$(git branch --show-current)" --state open --json number,title,url,baseRefName,headRefName,isDraft
```

Reject a detached HEAD, missing `origin`, missing GitHub authentication, ambiguous/non-GitHub `origin`, missing default branch, or default branch checked out for feature work. Discover the GitHub default base; do not hard-code `main`. All later `gh` reads and writes MUST use the resolved repository, and all pushes MUST target `origin` explicitly rather than following another configured upstream.

Classify the initial exact-head open PR query before any mutation. Zero or one match may proceed to the draft. More than one match is a hard stop: report every URL and do not validate, stage, commit, push, or edit GitHub state until the ambiguity is resolved.

Fetch remote metadata without rewriting local history when needed. Compare both commit ancestry and the full PR diff against the remote base:

```bash
git log --oneline "origin/<base>..HEAD"
git diff --name-status "origin/<base>...HEAD"
git diff --stat "origin/<base>...HEAD"
git diff "origin/<base>...HEAD"
```

Inspect the paths and content, not only the stat. If the branch contains earlier commits outside the requested unit, has an unexpected base, or would publish a materially broader diff, call that out in the draft. When one open PR exists, compare its base with the proposed base before mutation; either keep it or include the exact base update in the approval plan. Do not silently create a new branch, cherry-pick, or change the base. The user must approve the broader PR or separately authorize isolation.

### 2. Resolve `$ARGUMENTS`

Parse only the forms in the input contract, validate the issue against the discovered repository, and record its number, title, state, and URL. An invalid supplied argument is a hard stop before staging, committing, pushing, PR editing, or commenting.

### 3. Build the exact change manifest

Derive candidate files from the user's requested task, the active or just-completed OpenSpec change, and the actual diff. Do not use all dirty files as the candidate set.

For every candidate path, inspect both unstaged and staged content:

```bash
git diff -- "<path>"
git diff --cached -- "<path>"
```

Present an exact path list and a concise reason each path belongs. Also summarize excluded dirty paths so it is clear they remain untouched.

If one file mixes requested and unrelated hunks, either exclude it or propose explicit patch staging. Never stage the whole file. Patch staging must be interactive or otherwise produce a reviewable patch; do not synthesize an opaque patch from memory.

Inspect the entire index. If any staged path or hunk is outside the proposed manifest, stop before changing the index. Ask the user to resolve it or explicitly include it. Do not unstage it yourself. If staged content is inside the manifest, include its exact diff in the approval draft.

### 4. Select fresh validations

Read repository instructions and build manifests to select all checks relevant to the approved files. The plan must name exact commands. Typical NexusWiki checks include:

- Python: focused `uv run pytest ...`, then applicable `uv run ruff check ...`.
- Dashboard: applicable `pnpm --dir apps/dashboard test`, `typecheck`, and `lint`.
- OpenSpec change artifacts: `openspec validate <change> --strict`.
- Main OpenSpec specs: `openspec validate --specs`.

Do not claim a check is unavailable until inspecting the relevant manifest or configuration. Prefer the narrowest complete check set, but include repository-mandated broader checks. Every result used for the commit decision must be from this run.

### 5. Draft the complete mutation plan

Before staging or any GitHub mutation, show one review block containing:

- resolved repository, head branch, remote, and base branch;
- supplied issue or an explicit “no issue linkage” statement;
- existing open PR state;
- commit ancestry and PR diff warnings;
- exact files and, when needed, exact hunks to commit;
- excluded dirty and staged changes;
- exact validation commands;
- Korean conventional commit message following `.claude/CLAUDE.md`;
- PR title and full body, including summary, test plan, and optional `Closes #N` line;
- exact mutation sequence: stage, verify index, commit, push, create/reuse PR, optional issue comment.

Ask for explicit approval. A previous request to implement or continue is not approval of this commit/PR draft. If the user changes scope, base, metadata, or commands, refresh the complete draft and ask again.

### 6. Validate before staging

After approval, run every planned validation. Stop on the first required failure or run the independent checks and report all failures, depending on cost. In either case, do not stage or commit after a failure.

Report the failing command, relevant output, and unchanged mutation state. Fixing failures is outside this skill unless the user separately asks for a fix.

### 7. Stage only the approved scope

Re-run `git status --short` and `git diff --cached` immediately before staging. If state has materially changed since approval, stop and refresh the draft.

For whole-file scope, use explicit literal paths:

```bash
git add -- "path/one" "path/two"
```

For mixed files, use the approved patch-staging approach. After staging, inspect:

```bash
git diff --cached --name-status
git diff --cached --stat
git diff --cached
```

The staged diff must match the approved manifest and hunks exactly. If it does not, stop without resetting or unstaging; report the mismatch and ask the user how to proceed.

### 8. Commit and verify

Create one commit with the approved message; do not amend:

```bash
git commit -m "<approved message>"
```

Verify the new SHA, subject, and committed paths:

```bash
git show --quiet --format='%H%n%s' HEAD
git diff-tree --no-commit-id --name-status -r HEAD
git status --short
```

If hooks modified files or the committed paths differ from approval, report the exact state and stop. Do not rewrite the commit automatically.

### 9. Push without force

Push the current branch normally. Add upstream only when it is absent:

```bash
git push origin <head-branch>
# or, when no upstream exists and tracking origin is desired:
git push -u origin <head-branch>
```

Never add a force flag and never push through a different configured upstream. On non-fast-forward or any push failure, re-query exact-head open PRs in the resolved repository, then stop and report the local commit SHA plus the verified GitHub PR state.

### 10. Create or reuse the PR

Query open PRs for the exact head branch again after push.

- No open PR: create one against the approved base with the approved title and body.
- Exactly one open PR: reuse it. Update title, body, or base only if those exact updates were in the approved plan.
- Multiple matches: stop and report them; do not guess.

Use origin-bound `gh pr create --repo <owner>/<repo>` or `gh pr edit --repo <owner>/<repo>` with a body file or safely quoted content. Never merge. Then verify with `gh pr view --repo <owner>/<repo> --json number,title,body,url,state,baseRefName,headRefName` and confirm the repository, head, base, title, and, when supplied, `Closes #N` line.

If create or edit exits unsuccessfully or returns an ambiguous response, immediately repeat the exact-head open PR query before retrying anything. Classify the result as confirmed created/reused, confirmed absent, multiple/ambiguous, or unknown due to query failure. Never retry creation while a PR might already exist.

### 11. Link the issue and report

If `$ARGUMENTS` resolved to an issue, inspect existing comments for the verified PR URL. Add a concise PR-link comment only when the same link is not already present. Verify the comment through a follow-up issue query.

Report these states independently:

- validations and exact commands;
- commit SHA and committed file count;
- push remote and branch;
- created or reused PR URL;
- issue closing keyword and comment state, when applicable;
- unrelated worktree/index changes still present.

If a later step fails, report the last verified successful state and a safe retry point. Never collapse partial success into either “all done” or “nothing changed.”

## Completion checklist

- [ ] `$ARGUMENTS` was omitted or resolved to the current repository's issue.
- [ ] The approved manifest and staged diff matched exactly.
- [ ] No unrelated staged change was altered or committed.
- [ ] Every required validation passed freshly.
- [ ] The commit paths and message were verified.
- [ ] The push used no force option.
- [ ] The PR was created once or an existing one was reused.
- [ ] The PR was not merged or auto-merged.
- [ ] The issue link was verified when an issue was supplied.
- [ ] Partial failures and remaining dirty state were reported accurately.

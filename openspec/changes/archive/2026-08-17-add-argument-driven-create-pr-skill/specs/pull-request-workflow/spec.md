## Purpose

개발 에이전트가 더러운 작업 트리에서도 승인된 변경 범위만 검증·commit하고, 선택한 GitHub 이슈와 추적 가능한 pull request를 안전하게 만들도록 한다.

## ADDED Requirements

### Requirement: ARGUMENTS issue resolution
The workflow SHALL accept an optional `$ARGUMENTS` value as a GitHub issue number, `#number`, or issue URL and SHALL validate that a supplied issue belongs to the current repository before any repository or GitHub mutation.

#### Scenario: Valid issue argument
- **WHEN** the user invokes `create-pr` with a current-repository issue number, hash-prefixed number, or issue URL
- **THEN** the workflow resolves the issue and includes `Closes #<number>` in the proposed PR body

#### Scenario: Invalid or foreign issue argument
- **WHEN** `$ARGUMENTS` cannot resolve to an issue in the current repository
- **THEN** the workflow stops before staging, committing, pushing, or changing GitHub state and reports the invalid argument

#### Scenario: No issue argument
- **WHEN** the user invokes `create-pr` without `$ARGUMENTS`
- **THEN** the workflow may create a PR without a closing keyword and does not invent an issue association

### Requirement: Explicit commit scope
The workflow SHALL derive and present an explicit file manifest for the requested work and SHALL preserve all unrelated working-tree and index changes.

#### Scenario: Dirty working tree with unrelated changes
- **WHEN** the repository contains requested and unrelated modifications
- **THEN** only the approved requested files or hunks are eligible for staging and commit, and unrelated changes remain unchanged

#### Scenario: Pre-staged changes outside the manifest
- **WHEN** the index contains a path or hunk outside the proposed manifest
- **THEN** the workflow stops before changing the index and asks the user to resolve or explicitly include it

#### Scenario: Mixed-scope file
- **WHEN** one file contains both requested and unrelated hunks
- **THEN** the workflow excludes the file or uses explicit patch staging only after showing the boundary, and never silently commits the whole file

### Requirement: Pre-mutation review gate
The workflow SHALL show the file manifest, validation plan, commit message, base branch, PR title, and PR body and obtain user approval before the first staging or external mutation.

#### Scenario: User approves the draft
- **WHEN** the user approves the complete draft
- **THEN** the workflow proceeds using the approved values

#### Scenario: User rejects or revises the draft
- **WHEN** the user rejects or changes any proposed value
- **THEN** the workflow performs no mutation until a revised complete draft is approved

### Requirement: Fresh validation before commit
The workflow SHALL run fresh validations relevant to the approved manifest and SHALL not claim success or create a commit when a required validation fails.

#### Scenario: All required validations pass
- **WHEN** every required project, test, lint, typecheck, and OpenSpec validation selected for the manifest succeeds
- **THEN** the workflow may stage and commit the approved scope

#### Scenario: Required validation fails
- **WHEN** any required validation fails
- **THEN** the workflow stops before commit and reports the failing command and remaining repository state

### Requirement: Safe commit, push, and PR publication
The workflow SHALL stage only approved paths or hunks, create one non-amended commit, push without force, and create or reuse a PR for the current branch without merging it.

#### Scenario: No PR exists for the branch
- **WHEN** validation and commit succeed and no open PR exists for the current branch
- **THEN** the workflow pushes the branch and creates a PR against the approved base branch

#### Scenario: An open PR already exists
- **WHEN** validation and commit succeed and an open PR already exists for the current branch
- **THEN** the workflow pushes the new commit, reuses the existing PR instead of creating a duplicate, and only applies approved metadata updates

#### Scenario: Unsafe operation would be required
- **WHEN** completion would require force-push, amend, merge, destructive index cleanup, or inclusion of an unapproved change
- **THEN** the workflow stops and requests separate user direction without performing that operation

### Requirement: Verified GitHub linkage
The workflow SHALL verify GitHub command responses before reporting success and SHALL comment the confirmed PR URL on a supplied tracking issue.

#### Scenario: PR publication succeeds with an issue argument
- **WHEN** GitHub confirms the created or reused PR and `$ARGUMENTS` resolved to an issue
- **THEN** the workflow comments the confirmed PR URL on that issue and reports the commit SHA and PR URL

#### Scenario: GitHub publication or comment fails
- **WHEN** push, PR creation or lookup, or issue commenting fails
- **THEN** the workflow reports the verified partial state and does not claim the failed action completed


# Pull Request Workflow Specification

## Purpose

개발 에이전트가 더러운 작업 트리에서도 승인된 변경 범위만 검증·commit하고, 선택한 GitHub 이슈와 추적 가능한 pull request를 안전하게 만들도록 한다.

## Requirements

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

### Requirement: 자동 운영 배포 전 마이그레이션 게이트
main 머지가 운영 애플리케이션 배포를 자동으로 시작하는 저장소에서, 마이그레이션을 포함한 PR의 운영자는 머지 전에 현재 운영 코드와의 호환성을 MUST 확인한다. 호환되는 마이그레이션은 머지 전에 운영 DB에 적용하고, 명령 응답으로 적용 원장과 해당 PR에 필요한 미적용 마이그레이션이 없음을 MUST 확인한다. 에이전트는 이 확인 없이 머지 준비가 완료됐다고 MUST NOT 보고한다. 이 게이트는 DB 쓰기나 머지 권한을 자동으로 부여하지 않는다.

#### Scenario: 이전 코드와 호환되는 마이그레이션
- **WHEN** main 머지가 자동 배포를 시작하고 PR에 현재 운영 코드와 호환되는 마이그레이션이 포함되어 있다
- **THEN** 운영자는 원격 원장과 dry-run 대상을 확인한 뒤 승인된 권한으로 DB에 선적용하고, 필요한 버전의 적용과 미적용 대상이 없음을 확인한 결과를 PR에 기록한 후에만 머지한다

#### Scenario: 적용 또는 확인이 완료되지 않았다
- **WHEN** 필요한 마이그레이션이 미적용 상태이거나 적용 결과를 확인할 권한 또는 명령 응답이 없다
- **THEN** PR은 머지하지 않고 필요한 운영자 조치와 확인되지 않은 상태를 보고한다

#### Scenario: 이전 운영 코드와 호환되지 않는다
- **WHEN** 마이그레이션 선적용이 현재 운영 코드의 동작을 깨뜨린다
- **THEN** 호환 단계로 변경을 분리하거나 자동 배포를 통제하는 별도 승인된 전환 계획을 마련하고, 그 계획의 선행 조건을 충족하기 전에는 머지하지 않는다

#### Scenario: 문서와 합성 증거만 바뀐다
- **WHEN** PR이 문서나 합성 증거만 변경하고 마이그레이션을 포함하지 않는다
- **THEN** 운영 DB 적용은 요구하지 않으며 마이그레이션 게이트가 해당하지 않음을 기록한다

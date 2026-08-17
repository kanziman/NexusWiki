## Purpose

기능 아이디어를 OpenSpec의 기존 산출물 구조 안에서 검증 가능한 요구사항, 기술 결정, 수직 구현 조각으로 점진적으로 확정하고 GitHub 작업 추적과 연결한다.

## ADDED Requirements

### Requirement: Progressive feature planning gates
The agent SHALL keep `proposal.md`, delta specs, `design.md`, and `tasks.md` as the feature planning source of truth and MUST use four approval gates: requirements and terminology, material architecture choice, final design and non-goals, and vertical task breakdown. It MUST ask only one unresolved material question at a time and include a recommended answer with its rationale.

#### Scenario: Feature idea contains material ambiguity
- **WHEN** a user requests a feature whose user flow, boundary behavior, or terminology would change the resulting contract
- **THEN** the agent investigates discoverable repository facts first and asks one remaining material question before finalizing the affected artifact

#### Scenario: Planning artifacts reach an approval boundary
- **WHEN** requirements, architecture alternatives, final design, or task breakdown are ready for review
- **THEN** the agent presents the corresponding artifact content and waits at that gate unless continuous authorization applies

### Requirement: Existing OpenSpec artifact responsibilities
The agent MUST capture fixed requirements and ubiquitous language in proposal/spec artifacts, ADR decisions and non-goals in design, and implementation slices in tasks. It MUST NOT create parallel `spec-fixed.md`, `prd.md`, or `issues.md` sources of truth.

#### Scenario: Feature planning completes
- **WHEN** all four planning stages have been approved or validly passed under continuous authorization
- **THEN** the complete feature contract exists in the standard OpenSpec artifacts without a duplicate feature-document hierarchy

### Requirement: Proportional architecture comparison
The agent SHALL compare three architecture alternatives across data structure, API impact, state management, core behavior, component structure, existing-pattern consistency, and testability when a material technical choice exists. It MUST use a concise decision rationale instead of inventing alternatives when the change has no material architecture choice.

#### Scenario: Material architecture choice exists
- **WHEN** two or more viable approaches would materially change data, interfaces, dependencies, or task decomposition
- **THEN** the agent presents three meaningful alternatives using the fixed comparison criteria before recording the selected ADR

#### Scenario: Change has one obvious implementation shape
- **WHEN** alternatives would be artificial and would not change the resulting contract or task plan
- **THEN** the agent records the selected approach and relevant rejected option without forcing a three-way comparison

### Requirement: Verifiable vertical task slices
Each implementation task SHALL be a dependency-ordered vertical slice that produces independently verifiable behavior and is normally completable within half a day to one day. Every slice MUST include Given-When-Then acceptance criteria and MUST NOT be split only by technical layer.

#### Scenario: Task plan spans API and UI
- **WHEN** a user-visible behavior requires persistence, API, and UI changes
- **THEN** the task plan groups the minimum cross-layer work into a verifiable behavior slice instead of separate persistence-only, API-only, and UI-only tasks

### Requirement: GitHub issue hierarchy and project tracking
The workflow MUST use a GitHub umbrella issue for each OpenSpec change and MUST create an approved vertical slice as a sub-issue of that umbrella. It SHALL add the umbrella and sub-issues to `kanziman` Project #1 with `Todo` as the initial status, record issue links in `tasks.md`, close only verified slice issues, and close the umbrella only after successful archive.

#### Scenario: New change planning starts
- **WHEN** no matching GitHub umbrella issue exists
- **THEN** the agent creates one, creates the OpenSpec change, links its path in the issue, and confirms both operations from command responses

#### Scenario: Vertical tasks are approved
- **WHEN** Gate 4 approves the task breakdown
- **THEN** the agent creates one GitHub sub-issue per slice, adds each to Project #1 as `Todo`, and records the returned issue identifiers in `tasks.md`

#### Scenario: External update cannot be confirmed
- **WHEN** GitHub or Project metadata is unavailable or a command does not confirm success
- **THEN** the agent does not guess identifiers or report the external transition as complete

### Requirement: Shared Codex and Claude propose contract
The project SHALL expose the same enhanced `openspec-propose` behavior to Codex and Claude while retaining the existing command name and standard OpenSpec artifact identifiers.

#### Scenario: Either supported agent starts a proposal
- **WHEN** Codex invokes the `openspec-propose` skill or Claude invokes the existing propose command
- **THEN** both entrypoints apply the same interview, gate, artifact, validation, and GitHub tracking contract

## Purpose

개발자가 인증, 데이터베이스, API를 준비하지 않고도 로컬 NexusWiki 제품 흐름을
안전하고 결정적으로 검토할 수 있는 목업 미리보기 환경을 제공한다.

## ADDED Requirements

### Requirement: Development-only product preview

The system SHALL provide a `/preview` route tree that is available only while
the dashboard runs in the development environment. It MUST render the preview
tree as not found in production and MUST NOT weaken authentication or
authorization for any non-preview route.

#### Scenario: Local reviewer opens the preview home

- **WHEN** a reviewer opens `/preview` on a development dashboard server
- **THEN** the system renders a mock signed-in workspace home without requiring
  Supabase credentials, a user session, or an API service

#### Scenario: Production request targets preview

- **WHEN** a request targets any `/preview` route in a production dashboard
- **THEN** the system returns the normal not-found outcome without rendering
  preview data

### Requirement: Representative mock workspace exploration

The system SHALL provide one deterministic mock user and workspace with
representative source, wiki, graph, backlog, member, and conversation data.
It MUST let a reviewer navigate preview home, sources, Ask, wiki, backlog, and
settings screens while keeping all preview navigation under `/preview`.

#### Scenario: Reviewer explores a mock document

- **WHEN** a reviewer opens a wiki document from a preview screen
- **THEN** the system displays the corresponding mock document and does not
  query a live workspace

#### Scenario: Reviewer follows a citation from mock Ask

- **WHEN** a reviewer activates a citation in the preview Ask conversation
- **THEN** the system displays the matching mock wiki or source evidence within
  the preview Ask destination

### Requirement: Safe preview interactions

The system SHALL preserve reviewable client-side interactions such as
navigation, filters, tabs, and deterministic mock Ask responses. It MUST NOT
perform requests that create, update, delete, upload, invite, or sign out;
instead it MUST present a Korean notice that the action is not saved in
preview.

#### Scenario: Reviewer attempts a state-changing action

- **WHEN** a reviewer submits an upload, invitation, settings, workspace, or
  session-changing control in preview
- **THEN** the system makes no external request and informs the reviewer that
  the action is not saved in preview

## MODIFIED Requirements

### Requirement: Workspace-scoped home overview
The system SHALL show a workspace-scoped home hero whose `h1` is the fixed page title `홈 대시보드`. Active workspace identity SHALL be conveyed by the workspace shell (LNB `WorkspaceSwitcher`); the home page MUST NOT add a `workspaces` query to place the workspace name in the hero `h1`. The hero SHALL include a knowledge-completeness indicator derived from the verification rate of compiled wiki pages in that workspace, and a compact sentence summarizing the workspace's source count and compiled wiki count. The system SHALL show URL-scoped links to add a source, ask a question, and browse wiki content. The system SHALL present four knowledge-health metric surfaces for that workspace: compiled wiki count with verification rate, connected source count with indexed chunk count, unresolved backlog count, and last-updated relative time taken from the server-render snapshot. The last-updated metric MUST NOT be presented as a live or realtime value.

#### Scenario: Returning member opens home
- **WHEN** a workspace member opens the workspace home route
- **THEN** the system shows only that workspace's overview and URL-scoped next actions

#### Scenario: Member reads knowledge-health metrics
- **WHEN** a workspace member opens home of a workspace that has compiled wiki pages or sources
- **THEN** the overview shows that workspace's verification rate, source count, indexed chunk count, backlog count, and a relative last-updated time without implying a live subscription

### Requirement: Ask hero canvas and suggested question chips
The system SHALL provide an Ask hero canvas with multi-line question input, search scope selection (workspace-wide, category, local context), a submit trigger leading to the ask interface, and clickable starter question chips that automatically populate the input. Suggested chips SHALL be supplied from the active workspace's compiled wiki page titles ranked by citation frequency, where citation frequency is the length of each page's `sources` array, and SHALL include at most four titles. The Ask hero MUST NOT present hardcoded starter questions from a domain unrelated to the active workspace. When submitted, the target ask interface SHALL automatically receive the query parameter and initiate the answering turn.

#### Scenario: User enters question via chips
- **WHEN** a member clicks a suggested question chip in the Ask hero canvas
- **THEN** the system fills the question input with the chip's text and focuses the input

#### Scenario: User submits question with scope
- **WHEN** a member enters a question and clicks submit
- **THEN** the system transitions to the ask page with the query and chosen scope, and the ask interface automatically begins generating the response

#### Scenario: Chips reflect the active workspace
- **WHEN** a member opens home of a workspace that has compiled wiki pages with source citations
- **THEN** the Ask hero presents those highly cited wiki titles as starter chips and does not present hardcoded engineering-domain questions

#### Scenario: Workspace has no wiki pages to suggest
- **WHEN** a member opens home of a workspace that has no compiled wiki pages
- **THEN** the Ask hero still provides the question input and submit control and does not present hardcoded starter chips from another domain

### Requirement: Two-column knowledge grid with wiki pages and backlog
The system SHALL display a two-column knowledge grid with an asymmetric desktop hierarchy that gives compiled wiki documents more width than the unresolved backlog. The left column SHALL feature recent compiled wiki documents (capped at 10 items) with category, verification, and citation-count badges. The right column SHALL feature unresolved red link backlog entries (capped at 8 items) with citation counts and a source-connection CTA that navigates to the workspace source-ingestion route with the backlog title prefilled and the text tab selected. Category labels SHALL match the existing knowledge-grid mapping (`concepts` 개념, `entities` 엔티티, `guides` 가이드, `maps` 맵).

#### Scenario: Populated wiki and backlog display
- **WHEN** a workspace has compiled wiki pages and unresolved links
- **THEN** the system displays up to 10 recent wiki document rows with category, verification, and citation-count badges, and up to 8 backlog rows with citation counts and a source connection CTA

#### Scenario: Empty state display
- **WHEN** a workspace has no compiled wiki pages or backlog items
- **THEN** the system displays descriptive empty state guidance encouraging the member to add their first source

#### Scenario: Member follows a backlog source-connection CTA
- **WHEN** a member activates the source-connection action on a home backlog row
- **THEN** the system navigates to the workspace source-ingestion route with that backlog title as a prefill query and the text tab selected

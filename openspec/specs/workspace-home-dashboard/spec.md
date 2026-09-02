# workspace-home-dashboard Specification

## Purpose

워크스페이스 멤버가 자료 등록, 질문, 위키 탐색을 시작하고 최근 활동을 확인할 수 있는 RLS-scoped home dashboard를 제공한다.

## Requirements

### Requirement: Workspace-scoped home overview
The system SHALL show a workspace-scoped home hero whose `h1` is the fixed page title `홈 대시보드`. Active workspace identity SHALL be conveyed by the workspace shell (LNB `WorkspaceSwitcher`); the home page MUST NOT add a `workspaces` query to place the workspace name in the hero `h1`. The hero SHALL include a knowledge-completeness indicator derived from the verification rate of compiled wiki pages in that workspace, and a compact sentence summarizing the workspace's source count and compiled wiki count. The system SHALL show URL-scoped links to add a source, ask a question, and browse wiki content. The system SHALL present four knowledge-health metric surfaces for that workspace: compiled wiki count with verification rate, connected source count with indexed chunk count, unresolved backlog count, and last-updated relative time taken from the server-render snapshot. The last-updated metric MUST NOT be presented as a live or realtime value.

#### Scenario: Returning member opens home
- **WHEN** a workspace member opens the workspace home route
- **THEN** the system shows only that workspace's overview and URL-scoped next actions

#### Scenario: Member reads knowledge-health metrics
- **WHEN** a workspace member opens home of a workspace that has compiled wiki pages or sources
- **THEN** the overview shows that workspace's verification rate, source count, indexed chunk count, backlog count, and a relative last-updated time without implying a live subscription

### Requirement: Recent workspace activity
The system SHALL show recent sources and wiki pages visible to the requester, with useful empty states when none exist.

#### Scenario: New workspace
- **WHEN** the active workspace has no sources or wiki pages
- **THEN** the system guides the member to add the first source

#### Scenario: Populated workspace
- **WHEN** the active workspace has recent sources or wiki pages
- **THEN** the system displays those records without exposing another workspace's data

### Requirement: Workspace shell navigation and layout
The system SHALL provide a responsive three-pane workspace shell layout consisting of a left navigation bar (LNB / sidebar), a top navigation bar, and a main content area styled with v2 design tokens.

#### Scenario: Desktop viewport layout
- **WHEN** a member views a workspace page on a desktop viewport (900px, 1280px, 1680px)
- **THEN** the system displays the persistent sidebar, topbar, and content area without horizontal scroll

#### Scenario: Mobile viewport responsive adaptation
- **WHEN** a member views a workspace page on a mobile viewport (390px, 640px)
- **THEN** the system collapses the sidebar into a drawer menu accessible via a topbar trigger without horizontal scroll

### Requirement: Workspace vocabulary consistency in entry flows
The system SHALL use 'workspace' (워크스페이스) terminology across all entry views and chooser components, avoiding legacy project terms.

#### Scenario: User views workspace chooser
- **WHEN** a user navigates to the workspace entry chooser view
- **THEN** the interface refers exclusively to workspaces and displays no legacy project vocabulary

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

### Requirement: Category lens filtering
The system SHALL provide category lens filters (all, concepts, entities, guides, maps) that filter the displayed compiled wiki pages by category.

#### Scenario: User filters by category
- **WHEN** a member selects a category filter (e.g. concepts)
- **THEN** the knowledge grid updates to show only wiki pages belonging to the selected category

### Requirement: Two-column knowledge grid with wiki pages and backlog
The system SHALL display a two-column knowledge grid with an asymmetric desktop hierarchy that gives compiled wiki documents more width than the unresolved backlog. The left column SHALL feature recent compiled wiki documents (capped at 5 items) with category, verification, and citation-count badges. The right column SHALL feature unresolved red link backlog entries (capped at 4 items) with citation counts and a source-connection CTA that navigates to the workspace source-ingestion route with the backlog title prefilled and the text tab selected. Each column SHALL expose a link to its dedicated full-list route so that items beyond the cap remain reachable. Category labels SHALL match the existing knowledge-grid mapping (`concepts` 개념, `entities` 엔티티, `guides` 가이드, `maps` 맵).

#### Scenario: Populated wiki and backlog display
- **WHEN** a workspace has compiled wiki pages and unresolved links
- **THEN** the system displays up to 5 recent wiki document rows with category, verification, and citation-count badges, and up to 4 backlog rows with citation counts and a source connection CTA

#### Scenario: Empty state display
- **WHEN** a workspace has no compiled wiki pages or backlog items
- **THEN** the system displays descriptive empty state guidance encouraging the member to add their first source

#### Scenario: Member follows a backlog source-connection CTA
- **WHEN** a member activates the source-connection action on a home backlog row
- **THEN** the system navigates to the workspace source-ingestion route with that backlog title as a prefill query and the text tab selected

#### Scenario: Workspace has more items than the home grid shows
- **WHEN** a workspace has more compiled wiki pages than the wiki cap or more unresolved backlog entries than the backlog cap
- **THEN** each column still renders only up to its cap and offers a link to that column's dedicated route where the remaining items are reachable

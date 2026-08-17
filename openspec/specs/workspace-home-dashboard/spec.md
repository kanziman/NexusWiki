# workspace-home-dashboard Specification

## Purpose

워크스페이스 멤버가 자료 등록, 질문, 위키 탐색을 시작하고 최근 활동을 확인할 수 있는 RLS-scoped home dashboard를 제공한다.

## Requirements

### Requirement: Workspace-scoped home overview
The system SHALL show the active workspace name, a compact source and wiki summary, and links to add a source, ask a question, and browse wiki content.

#### Scenario: Returning member opens home
- **WHEN** a workspace member opens the workspace home route
- **THEN** the system shows only that workspace's overview and URL-scoped next actions

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
The system SHALL provide an Ask hero canvas with multi-line question input, search scope selection (workspace-wide, category, local context), a submit trigger leading to the ask interface, and clickable starter question chips that automatically populate the input.

#### Scenario: User enters question via chips
- **WHEN** a member clicks a suggested question chip in the Ask hero canvas
- **THEN** the system fills the question input with the chip's text and focuses the input

#### Scenario: User submits question with scope
- **WHEN** a member enters a question and clicks submit
- **THEN** the system transitions to the ask page with the query and chosen scope

### Requirement: Category lens filtering
The system SHALL provide category lens filters (all, concepts, entities, guides, maps) that filter the displayed compiled wiki pages by category.

#### Scenario: User filters by category
- **WHEN** a member selects a category filter (e.g. concepts)
- **THEN** the knowledge grid updates to show only wiki pages belonging to the selected category

### Requirement: Two-column knowledge grid with wiki pages and backlog
The system SHALL display a two-column knowledge grid featuring recent compiled wiki documents with verification status badges on the left, and unresolved red link backlog entries with source connection prompts on the right.

#### Scenario: Populated wiki and backlog display
- **WHEN** a workspace has compiled wiki pages and unresolved links
- **THEN** the system displays the wiki document rows with category and verification badges, and the backlog rows with citation counts and a source connection CTA

#### Scenario: Empty state display
- **WHEN** a workspace has no compiled wiki pages or backlog items
- **THEN** the system displays descriptive empty state guidance encouraging the member to add their first source

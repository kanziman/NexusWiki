## ADDED Requirements

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

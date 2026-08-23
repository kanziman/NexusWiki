## MODIFIED Requirements

### Requirement: Ask hero canvas and suggested question chips
The system SHALL provide an Ask hero canvas with multi-line question input, search scope selection (workspace-wide, category, local context), a submit trigger leading to the ask interface, and clickable starter question chips that automatically populate the input. When submitted, the target ask interface SHALL automatically receive the query parameter and initiate the answering turn.

#### Scenario: User enters question via chips
- **WHEN** a member clicks a suggested question chip in the Ask hero canvas
- **THEN** the system fills the question input with the chip's text and focuses the input

#### Scenario: User submits question with scope
- **WHEN** a member enters a question and clicks submit
- **THEN** the system transitions to the ask page with the query and chosen scope, and the ask interface automatically begins generating the response

### Requirement: Two-column knowledge grid with wiki pages and backlog
The system SHALL display a two-column knowledge grid featuring recent compiled wiki documents (capped at 10 items) with verification status badges on the left, and unresolved red link backlog entries (capped at 8 items) with source connection prompts on the right.

#### Scenario: Populated wiki and backlog display
- **WHEN** a workspace has compiled wiki pages and unresolved links
- **THEN** the system displays up to 10 recent wiki document rows with category and verification badges, and up to 8 backlog rows with citation counts and a source connection CTA

#### Scenario: Empty state display
- **WHEN** a workspace has no compiled wiki pages or backlog items
- **THEN** the system displays descriptive empty state guidance encouraging the member to add their first source

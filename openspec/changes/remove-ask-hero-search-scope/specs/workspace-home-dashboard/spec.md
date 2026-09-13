## MODIFIED Requirements

### Requirement: Ask hero canvas and suggested question chips
The system SHALL provide an Ask hero canvas with multi-line question input, a submit trigger leading to the ask interface, and clickable starter question chips that automatically populate the input. Suggested chips SHALL be supplied from the active workspace's compiled wiki page titles ranked by citation frequency, where citation frequency is the length of each page's `sources` array, and SHALL include at most four titles. The Ask hero MUST NOT present hardcoded starter questions from a domain unrelated to the active workspace. The Ask hero MUST NOT present a search-scope selector. When submitted, the target ask interface SHALL automatically receive the query parameter and initiate the answering turn. Retrieval for that turn SHALL use the workspace-wide search already owned by grounded answering; the home hero MUST NOT attach a scope query or otherwise claim a narrower search range.

#### Scenario: User enters question via chips
- **WHEN** a member clicks a suggested question chip in the Ask hero canvas
- **THEN** the system fills the question input with the chip's text and focuses the input

#### Scenario: User submits question with scope
- **WHEN** a member enters a question and clicks submit
- **THEN** the system transitions to the ask page with the query only, without a search-scope query parameter, and the ask interface automatically begins generating the response

#### Scenario: Chips reflect the active workspace
- **WHEN** a member opens home of a workspace that has compiled wiki pages with source citations
- **THEN** the Ask hero presents those highly cited wiki titles as starter chips and does not present hardcoded engineering-domain questions

#### Scenario: Workspace has no wiki pages to suggest
- **WHEN** a member opens home of a workspace that has no compiled wiki pages
- **THEN** the Ask hero still provides the question input and submit control and does not present hardcoded starter chips from another domain

#### Scenario: Member looks for a search-scope control
- **WHEN** a member opens the workspace home Ask hero
- **THEN** the canvas does not offer workspace-wide, category, or current-document-neighborhood scope options

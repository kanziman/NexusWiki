## ADDED Requirements

### Requirement: Unresolved red-link backlog aggregation and sorting
The system SHALL aggregate unresolved wiki links (`to_wiki_id IS NULL`) by `target_slug` in the backlog view, sorted by reference count (`impact`) descending.

#### Scenario: Member views backlog list
- **WHEN** a member navigates to `/w/[workspaceId]/backlog`
- **THEN** the system displays aggregated backlog topics with their impact count, first detected timestamp, and referencing wiki pages

### Requirement: Source ingestion guidance from backlog topics
The system SHALL provide a '소스 추가' action on each backlog item that navigates to the source ingestion view with `prefillTitle` and `tab=text`.

#### Scenario: Member clicks source addition for a backlog topic
- **WHEN** a member clicks '소스 추가' on a backlog topic
- **THEN** the system navigates to `/w/[workspaceId]/sources?prefillTitle=<slug>&tab=text`

### Requirement: Real-time ask SSE streaming and citation markers
The system SHALL stream LLM answers via SSE events (`meta`, `delta`, `citations`, `done`), render citations with active markers once resolved, and handle connection errors gracefully.

#### Scenario: Member submits question in ask view
- **WHEN** a member submits a query in the Ask view
- **THEN** the system streams tokens in real-time and converts citation anchors into clickable inspection chips upon receiving citations

## MODIFIED Requirements

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

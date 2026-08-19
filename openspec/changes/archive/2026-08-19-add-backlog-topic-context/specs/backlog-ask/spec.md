## MODIFIED Requirements

### Requirement: Unresolved red-link backlog aggregation and sorting
The system SHALL aggregate unresolved wiki links (`to_wiki_id IS NULL`) by `target_slug` in the backlog view, sorted by reference count (`impact`) descending. Each aggregated topic SHALL carry a display title recovered from the `[[...]]` spelling in its referencing wiki bodies, falling back to the de-slugified `target_slug` when no spelling is found.

#### Scenario: Member views backlog list
- **WHEN** a member navigates to `/w/[workspaceId]/backlog`
- **THEN** the system displays aggregated backlog topics with their impact count, first detected timestamp, and referencing wiki pages

#### Scenario: Referencing bodies spell a topic differently
- **WHEN** the wiki pages referencing one topic contain more than one distinct `[[...]]` spelling
- **THEN** the system displays the most frequent spelling, breaking ties by the referencing page title in ascending order, so the label is identical on every render

#### Scenario: No original spelling survives in any referencing body
- **WHEN** no referencing wiki body contains a `[[...]]` occurrence for the topic
- **THEN** the system displays the de-slugified `target_slug` and still shows the raw slug alongside it

## ADDED Requirements

### Requirement: Backlog topic detail panel with server-side citation context
The system SHALL provide a detail panel for a selected backlog topic showing its display title, first detected timestamp, referencing wiki pages, one citation excerpt per referencing page, and the same source ingestion action offered in the list. Excerpts SHALL be produced on the server, and full wiki page bodies SHALL NOT be transferred to the client.

#### Scenario: Member opens a backlog topic
- **WHEN** a member selects a backlog topic row
- **THEN** the system opens the detail panel showing the topic, its first detected timestamp, each referencing wiki page, and an excerpt of the text surrounding the reference in that page

#### Scenario: Detail panel renders reference markup
- **WHEN** an excerpt or display title contains wiki link markup
- **THEN** the system renders the spelling as plain text and never exposes the surrounding brackets

#### Scenario: Member requests source ingestion from the detail panel
- **WHEN** a member activates the source action inside the detail panel
- **THEN** the system navigates to `/w/[workspaceId]/sources?prefillTitle=<display title>&tab=text`, matching the list row action

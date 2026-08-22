## ADDED Requirements

### Requirement: Compact accessible knowledge-surface controls
The system SHALL present workspace navigation, library toolbars, status badges, empty states, and source-ingestion controls with a consistent compact hierarchy. Keyboard focus MUST remain visibly distinguishable, and collapsed navigation controls MUST retain an accessible name and a pointer-visible label without exposing clipped text.

#### Scenario: Member operates compact controls with a keyboard
- **WHEN** a member tabs through the sidebar, search fields, filters, upload tabs, and modal actions
- **THEN** every interactive control exposes an accessible name, a visible focus treatment, and a state that does not rely on color alone

#### Scenario: Member uses the collapsed sidebar
- **WHEN** the member collapses the workspace sidebar and points to or focuses a workspace or account control
- **THEN** the control remains operable by its icon and accessible name, and its full label can be identified without expanding the sidebar

#### Scenario: Member opens source ingestion
- **WHEN** the member opens the source upload modal and switches among file, URL, and text registration
- **THEN** the active registration mode, required fields, progress or per-file outcomes, errors, and primary submit action remain visually and semantically distinct

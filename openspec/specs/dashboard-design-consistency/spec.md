# dashboard-design-consistency Specification

## Purpose

워크스페이스 멤버가 dashboard 전반에서 같은 정보 위계와 조작 방식을 통해 지식 작업을 빠르고 신뢰감 있게 수행하도록 한다.

## Requirements

### Requirement: Consistent workspace page structure
The system SHALL present every workspace destination with a consistent page frame containing a page title, contextual supporting information where applicable, and a readable content width. Destinations that render on the shared content canvas SHALL all use one and the same maximum content width, so that moving between them does not shift the left and right boundaries. A destination that owns a purpose-built layout is exempt from that shared width and SHALL keep the width its own layout defines — for example the Ask workspace, whose split boundary the member controls directly, and the document reader, whose narrower measure exists to keep prose readable. Primary actions and secondary controls SHALL use the same visual hierarchy across destinations. Where Wiki and Graph are presented as content-viewer tabs within the unified Ask destination rather than standalone destinations, each tab SHALL preserve this same page-frame consistency on switch. Contextual supporting labels SHALL appear only where they carry information the page title does not already convey, so that decorative context markers do not repeat on every destination.

#### Scenario: Member moves between workspace destinations
- **WHEN** a member navigates between Home, Sources, Ask, and Settings
- **THEN** each destination preserves a recognizable title, content frame, action hierarchy, and keyboard focus treatment

#### Scenario: Member switches content viewer tabs within Ask
- **WHEN** a member switches the content viewer between the wiki document, raw source, knowledge graph, and mind map tabs
- **THEN** each tab preserves a recognizable title, content frame, and keyboard focus treatment consistent with the other workspace destinations

#### Scenario: Member compares shared-canvas destinations on a wide viewport
- **WHEN** a member opens two different destinations that render on the shared content canvas on the same wide viewport
- **THEN** both content areas begin and end at the same horizontal boundaries, with neither rendering measurably narrower than the other

#### Scenario: Member opens a destination that owns its layout
- **WHEN** a member opens the Ask workspace or the document reader on a wide viewport
- **THEN** that destination keeps the width its own layout defines rather than being forced to the shared canvas width

#### Scenario: Member scans destinations for repeated decorative context
- **WHEN** a member navigates across all workspace destinations
- **THEN** contextual supporting labels appear only on destinations where they add information beyond the page title, rather than once on every destination

### Requirement: Shared state and control language
The system SHALL use consistent accessible controls and semantic status presentation for filters, inputs, actions, loading, empty, error, success, warning, and destructive states. A given underlying status value SHALL be presented with the same label wherever it appears, so that one state is never named differently on two destinations. A given destination SHALL likewise carry one canonical name across every surface that refers to it — navigation, breadcrumb, page heading, and any summary section on another destination — including the accessible name exposed to assistive technology. A surface MAY append a parenthetical gloss after that canonical name, but MUST NOT replace it with a different term. Status text SHALL be rendered at a size that remains legible rather than shrunk to a decorative marker.

#### Scenario: Member encounters a non-default state
- **WHEN** a destination displays an empty, error, processing, verification, or no-results state
- **THEN** the state communicates what happened, what remains possible, and any next action using text in addition to color

#### Scenario: Member sees the same underlying status on two destinations
- **WHEN** a wiki page whose verification status is `verified` appears on both the workspace home and the wiki library
- **THEN** both destinations label that status identically

#### Scenario: Member reaches one destination from several surfaces
- **WHEN** a member sees a destination referenced from workspace navigation, from a breadcrumb, and from a summary section on another destination
- **THEN** every one of those references names it with the same canonical term, and the destination's own heading uses that same term

#### Scenario: Assistive technology user hears a destination name
- **WHEN** a screen reader announces a navigation control or region for a destination whose visible label is that destination's canonical name
- **THEN** the announced accessible name matches the visible canonical name rather than an older or alternate term

### Requirement: Constrained global knowledge actions
The system SHALL limit the workspace-level global action bar to the two primary knowledge actions — adding a source and starting a question — so that destination-specific actions do not accumulate in shared chrome. Account and navigation controls are governed separately and are not counted as global knowledge actions.

#### Scenario: Member views the global action bar
- **WHEN** a member opens any workspace destination
- **THEN** the global action bar offers adding a source and starting a question, and no additional destination-specific knowledge action

#### Scenario: A destination needs its own action
- **WHEN** a destination requires an action that applies only to that destination
- **THEN** that action is presented within the destination's own content frame rather than added to the global action bar

### Requirement: Responsive knowledge-work layout
The system SHALL maintain readable document content, touch-accessible controls, and prioritized information on narrow viewports without hiding available primary actions.

#### Scenario: Member uses a narrow viewport
- **WHEN** a member opens any workspace destination on a narrow viewport
- **THEN** navigation, controls, and primary content reflow without horizontal overflow or unreadable text columns

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

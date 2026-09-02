## MODIFIED Requirements

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

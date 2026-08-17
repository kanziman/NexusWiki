## ADDED Requirements

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

## ADDED Requirements

### Requirement: Workspace settings 3-tab layout
The system SHALL provide a three-tab settings navigation layout consisting of '일반' (General), '멤버' (Members), and '운영 현황' (Operations).

#### Scenario: Member navigates settings tabs
- **WHEN** a member navigates to `/w/[workspaceId]/settings`
- **THEN** the system displays the settings header, tab list, and defaults to the '일반' or '멤버' panel based on user interaction

#### Scenario: Viewer/Editor role access to Operations tab
- **WHEN** the active user has 'owner' or 'editor' role
- **THEN** the system displays the '운영 현황' tab
- **WHEN** the active user has 'viewer' role
- **THEN** the system does not render the '운영 현황' tab

### Requirement: Workspace general settings management
The system SHALL allow viewing workspace name and slug, and allow only the workspace owner to update them with validation.

#### Scenario: Owner edits workspace name and slug
- **WHEN** an owner updates the name or slug with valid format and saves
- **THEN** the system persists the change to the database and displays success feedback

#### Scenario: Non-owner views general settings
- **WHEN** a viewer or editor opens the general settings panel
- **THEN** the input fields are disabled or read-only with a message indicating only owners can modify settings

### Requirement: Role-gated member invitation
The system SHALL strictly gate the member invitation form so that it is only visible and accessible to workspace owners.

#### Scenario: Owner views members tab
- **WHEN** an owner opens the members tab
- **THEN** the system renders both the member roster and the invite form

#### Scenario: Non-owner views members tab
- **WHEN** an editor or viewer opens the members tab
- **THEN** the system renders the member roster but does not render the invite form

### Requirement: Operations snapshot display
The system SHALL display the monthly budget consumption in micro-dollar conversion and the 5-stage background job pipeline (parse, compile, link_sync, embed, conflict_check) with a manual refresh button.

#### Scenario: User refreshes operations snapshot
- **WHEN** an owner or editor clicks the refresh button in operations panel
- **THEN** the system re-fetches `/workspaces/{workspace_id}/operations` without automatic polling

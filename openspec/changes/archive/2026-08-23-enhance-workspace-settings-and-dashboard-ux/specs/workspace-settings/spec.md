## MODIFIED Requirements

### Requirement: Workspace general settings management
The system SHALL allow viewing workspace name, slug, and collaboration type (personal vs team), and allow only the workspace owner to update them with validation. When switching from a team workspace to a personal workspace, the system SHALL block the transition if other members are currently present in the workspace.

#### Scenario: Owner edits workspace name and slug
- **WHEN** an owner updates the name, slug, or type with valid format and saves
- **THEN** the system persists the change to the database, updates the shell switcher display, and displays success feedback

#### Scenario: Owner blocked from converting team workspace with active members to personal
- **WHEN** an owner attempts to change a team workspace to a personal workspace while other members are joined
- **THEN** the system prevents the update and presents clear guidance instructing the owner to remove all other members first

#### Scenario: Non-owner views general settings
- **WHEN** a viewer or editor opens the general settings panel
- **THEN** the input fields are disabled or read-only with a message indicating only owners can modify settings

### Requirement: Role-gated member invitation
The system SHALL strictly gate the member invitation form so that it is only accessible to workspace owners when the workspace is a team workspace. When the workspace is a personal workspace, the invitation form SHALL be disabled with guidance.

#### Scenario: Owner views members tab
- **WHEN** an owner opens the members tab in a team workspace
- **THEN** the system renders both the member roster and an enabled invite form

#### Scenario: Owner views members tab in personal workspace
- **WHEN** an owner opens the members tab in a personal workspace
- **THEN** the system renders the member roster and a disabled invite form explaining that personal workspaces cannot invite members

#### Scenario: Non-owner views members tab
- **WHEN** an editor or viewer opens the members tab
- **THEN** the system renders the member roster but does not render the invite form

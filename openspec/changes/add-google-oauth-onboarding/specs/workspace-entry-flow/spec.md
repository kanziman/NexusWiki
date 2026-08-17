## MODIFIED Requirements

### Requirement: RLS-scoped workspace entry resolution
The system SHALL determine an authenticated user's entry destination from only the workspaces visible to that requester. It MUST use a deterministic ordering when selecting a sole or default workspace and MUST present personal-workspace onboarding for a user with no accessible workspaces without naming or counting inaccessible workspaces.

#### Scenario: One accessible workspace
- **WHEN** an authenticated user has exactly one accessible workspace
- **THEN** the system redirects the user to that workspace's home route

#### Scenario: No accessible workspaces
- **WHEN** an authenticated user has no accessible workspaces
- **THEN** the system displays personal-workspace onboarding without naming or counting inaccessible workspaces

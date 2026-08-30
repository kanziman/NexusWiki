## ADDED Requirements

### Requirement: Workspace deletion with confirmation in Danger Zone
The system SHALL provide a '위험 구역' (Danger Zone) card in the general settings panel allowing only the workspace owner to permanently delete the workspace. The system SHALL require explicit confirmation by prompting the user to type the exact workspace name before enabling the final deletion action. Upon successful deletion, the system SHALL navigate the user to another available workspace, or to the workspace onboarding/creation flow if no other workspaces remain.

#### Scenario: Owner opens delete modal and confirms with exact workspace name
- **WHEN** the workspace owner clicks the '워크스페이스 삭제' button, types the exact workspace name in the confirmation modal, and submits
- **THEN** the system permanently deletes the workspace and its cascaded resources from the database, and redirects the user to the next available workspace or `/onboarding`

#### Scenario: Owner types mismatched workspace name
- **WHEN** the workspace owner enters a name that does not match the current workspace name in the confirmation modal
- **THEN** the system keeps the final delete button disabled

#### Scenario: Non-owner views Danger Zone in general settings
- **WHEN** a non-owner (editor or viewer) opens the general settings panel
- **THEN** the system renders the Danger Zone with the delete button disabled or hidden, accompanied by a note that only owners can delete the workspace

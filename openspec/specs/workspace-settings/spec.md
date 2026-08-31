# workspace-settings Specification

## Purpose

워크스페이스 멤버가 기본 정보(이름, 슬러그)를 확인/수정하고, 멤버 로스터 및 초대를 관리하며, 백그라운드 파이프라인 및 예산 운영 현황을 모니터링할 수 있는 RLS-scoped 설정 화면을 제공한다.

## Requirements

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

### Requirement: Operations snapshot display
The system SHALL display the monthly budget consumption in micro-dollar conversion and the 5-stage background job pipeline (parse, compile, link_sync, embed, conflict_check) with a manual refresh button.

#### Scenario: User refreshes operations snapshot
- **WHEN** an owner or editor clicks the refresh button in operations panel
- **THEN** the system re-fetches `/workspaces/{workspace_id}/operations` without automatic polling

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

### Requirement: BYOK custom AI API key management
The system SHALL allow workspace owners to configure, test, and remove a custom OpenRouter or OpenAI API key (Bring Your Own Key) in the general settings panel. Non-owners SHALL only see masked status or read-only indicators.

#### Scenario: Owner registers and saves a custom API key
- **WHEN** the workspace owner inputs a valid custom API key (e.g. `sk-or-v1-...`) and saves
- **THEN** the system persists the key, displays the masked key format (e.g. `sk-or-v1-••••••••1a2b`), and displays a success notification

#### Scenario: Owner deletes a custom API key
- **WHEN** the workspace owner clicks the delete/remove API key button and confirms
- **THEN** the system removes the custom key and reverts the workspace to the default free credit quota

#### Scenario: Non-owner views the general settings BYOK section
- **WHEN** a viewer or editor views the general settings panel
- **THEN** the API key input is disabled or masked without exposing the raw secret key


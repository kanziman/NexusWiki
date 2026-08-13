# workspace-entry-flow Specification

## Purpose

인증된 사용자가 권한 있는 워크스페이스만 안전하게 발견하고 선택하여 해당 지식 공간으로 진입하도록 한다.

## Requirements

### Requirement: RLS-scoped workspace entry resolution
The system SHALL determine an authenticated user's entry destination from only the workspaces visible to that requester. It MUST use a deterministic ordering when selecting a sole or default workspace and MUST retain the existing invitation guidance for a user with no accessible workspaces.

#### Scenario: One accessible workspace
- **WHEN** an authenticated user has exactly one accessible workspace
- **THEN** the system redirects the user to that workspace's home route

#### Scenario: No accessible workspaces
- **WHEN** an authenticated user has no accessible workspaces
- **THEN** the system displays the existing invitation guidance without naming or counting inaccessible workspaces

### Requirement: Explicit multi-workspace selection
The system SHALL present an explicit workspace selection surface when an authenticated user has two or more accessible workspaces. The surface MUST identify each selectable workspace and route the user to the selected workspace's home without creating a cross-workspace session state.

#### Scenario: Multiple accessible workspaces
- **WHEN** an authenticated user enters the application with two or more accessible workspaces
- **THEN** the system displays only those accessible workspaces for selection

#### Scenario: Selecting a workspace
- **WHEN** a user selects an accessible workspace from the entry surface
- **THEN** the system navigates to that workspace's URL-scoped home route

### Requirement: Workspace-scoped navigation continuity
The system SHALL keep Sources, Ask, Wiki, Graph, Settings, and workspace switching scoped to the workspace ID in the active URL after entry. The workspace switcher MUST expose only the requester's accessible workspaces.

#### Scenario: Switching workspaces after entry
- **WHEN** a user switches to another accessible workspace
- **THEN** the system navigates to that workspace's URL-scoped home route and subsequent navigation remains within it

### Requirement: Non-disclosing inaccessible workspace handling
The system SHALL preserve the generic protected-route outcome for a workspace ID that is inaccessible to the requester. It MUST not disclose whether that workspace exists or expose its content through entry or navigation flows.

#### Scenario: Tampered workspace URL
- **WHEN** an authenticated user opens a workspace URL for a workspace they cannot access
- **THEN** the system returns the generic protected-route outcome without rendering workspace data

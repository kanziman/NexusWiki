# account-session-control Specification

## Purpose

인증된 사용자가 현재 dashboard 세션을 안전하게 식별하고, 언제든지 명시적으로 종료할 수 있도록 한다.

## Requirements

### Requirement: Minimal authenticated account affordance
The system SHALL present an authenticated user with an account affordance in the dashboard header. It MUST identify the active session without exposing profile data that is unnecessary for session recognition and MUST remain keyboard accessible.

#### Scenario: Authenticated dashboard view
- **WHEN** an authenticated user views a workspace route
- **THEN** the header exposes an accessible account affordance for the active session

#### Scenario: Narrow viewport access
- **WHEN** an authenticated user uses the dashboard at a narrow viewport
- **THEN** the account affordance remains reachable without relying on pointer hover

### Requirement: Explicit session termination
The system SHALL offer a clearly named logout action from the account affordance. When the action succeeds, it MUST terminate the current authentication session and navigate the user to `/login`.

#### Scenario: Successful logout
- **WHEN** an authenticated user activates logout
- **THEN** the system ends the current session and displays the login route

#### Scenario: Keyboard logout
- **WHEN** a keyboard user opens the account affordance and activates logout
- **THEN** the system performs the same session termination and navigation

### Requirement: Protected route remains inaccessible after logout
The system SHALL retain the existing authentication protection for workspace routes after logout. It MUST not render workspace data when the former user revisits a protected workspace URL without a session.

#### Scenario: Revisiting a workspace after logout
- **WHEN** a logged-out user navigates to a `/w/<workspaceId>` route
- **THEN** the system redirects the user to the login route without rendering workspace data

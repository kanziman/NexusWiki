# workspace-home-dashboard Specification

## Purpose

워크스페이스 멤버가 자료 등록, 질문, 위키 탐색을 시작하고 최근 활동을 확인할 수 있는 RLS-scoped home dashboard를 제공한다.

## Requirements

### Requirement: Workspace-scoped home overview
The system SHALL show the active workspace name, a compact source and wiki summary, and links to add a source, ask a question, and browse wiki content.

#### Scenario: Returning member opens home
- **WHEN** a workspace member opens the workspace home route
- **THEN** the system shows only that workspace's overview and URL-scoped next actions

### Requirement: Recent workspace activity
The system SHALL show recent sources and wiki pages visible to the requester, with useful empty states when none exist.

#### Scenario: New workspace
- **WHEN** the active workspace has no sources or wiki pages
- **THEN** the system guides the member to add the first source

#### Scenario: Populated workspace
- **WHEN** the active workspace has recent sources or wiki pages
- **THEN** the system displays those records without exposing another workspace's data

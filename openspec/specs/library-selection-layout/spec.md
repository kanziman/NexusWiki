# library-selection-layout Specification

## Purpose

워크스페이스 멤버가 자료와 위키 라이브러리에서 같은 방식으로 항목을 열고 상세 맥락을 읽고 목록으로 돌아가도록 한다.

## Requirements

### Requirement: Consistent library selection
The system SHALL render selectable source and wiki items with a common document-row hierarchy that exposes title, supporting metadata, state, and a direct detail affordance.

#### Scenario: Member selects a library item
- **WHEN** a member activates a source or wiki item
- **THEN** the item presents a consistent selected-detail transition and preserves the active workspace scope

### Requirement: Consistent detail return path
The system SHALL provide a visible, accessible return path from source and wiki detail views to their respective library without relying on browser history.

#### Scenario: Member returns to a library
- **WHEN** a member is viewing a source or wiki detail
- **THEN** the member can activate a labelled link to return to the corresponding workspace library

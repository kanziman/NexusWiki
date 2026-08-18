## Purpose

워크스페이스 멤버가 URL 인코딩 방식과 관계없이 권한 있는 위키 상세 페이지를 안전하고 일관되게 열 수 있도록 한다.

## REMOVED Requirements

### Requirement: Canonical wiki slug lookup

**Reason**: 이 요구사항의 "Legacy wiki route redirects into the unified viewer" 시나리오가 리다이렉트를 계약으로 못박고 있어, 같은 라우트에서 리더를 렌더링하는 새 동작과 양립할 수 없다. 슬러그 디코딩·격리 경계 부분은 아래 대체 요구사항이 그대로 이어받는다.

## ADDED Requirements

### Requirement: Canonical wiki slug lookup and in-place reader

The system SHALL resolve a wiki detail route's slug to its decoded Unicode value before looking up the page within the active workspace, and SHALL render the wiki reader at that same route instead of redirecting elsewhere. It MUST preserve the existing requester session and workspace-scoped access boundary for the lookup.

#### Scenario: Percent-encoded Hangul slug
- **WHEN** an authenticated workspace member opens a wiki detail URL whose Hangul slug is percent-encoded
- **THEN** the system displays the matching wiki page in that workspace

#### Scenario: Already-decoded mixed slug
- **WHEN** an authenticated workspace member opens a wiki detail URL whose ASCII and Hangul slug is already decoded
- **THEN** the system displays the matching wiki page in that workspace

#### Scenario: ASCII slug compatibility
- **WHEN** an authenticated workspace member opens a wiki detail URL with an ASCII-only slug
- **THEN** the system displays the same matching wiki page as before

#### Scenario: Wiki route renders the reader in place
- **WHEN** an authenticated workspace member opens `/wiki/[slug]`
- **THEN** the system renders the wiki reader at that route with the document body and its table of contents, and does not navigate the member to the unified workspace viewer

## MODIFIED Requirements

### Requirement: Safe malformed-slug handling

The system SHALL handle a malformed percent-encoded wiki route slug without returning a server error or exposing page data. It MUST present the existing generic not-found state for an unresolvable or inaccessible page.

#### Scenario: Malformed percent encoding
- **WHEN** a user opens a wiki detail URL whose slug contains malformed percent encoding
- **THEN** the system returns the generic wiki not-found state without a 500 response

#### Scenario: Cross-workspace isolation
- **WHEN** a slug resolves to a page outside the active workspace or the requester lacks membership
- **THEN** the system does not reveal that page and returns the generic protected-route outcome

### Requirement: Wiki reader table of contents

The system SHALL present a table of contents beside the wiki document body on viewports wide enough to hold it, listing the document's headings and letting the member jump to a section. It MUST hide the panel rather than shrink the body on narrow viewports.

#### Scenario: Member jumps to a section
- **WHEN** a member selects a heading in the table of contents
- **THEN** the reader scrolls that section into view

#### Scenario: Narrow viewport
- **WHEN** the viewport is too narrow to hold the panel beside the body
- **THEN** the reader hides the table of contents and keeps the document body full width

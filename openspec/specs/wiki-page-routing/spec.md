# wiki-page-routing Specification

## Purpose

워크스페이스 멤버가 URL 인코딩 방식과 관계없이 권한 있는 위키 상세 페이지를 안전하고 일관되게 열 수 있도록 한다.

## Requirements

### Requirement: Canonical wiki slug lookup
The system SHALL resolve a wiki detail route's slug to its decoded Unicode value before looking up the page within the active workspace. It MUST preserve the existing requester session and workspace-scoped access boundary for the lookup.

#### Scenario: Percent-encoded Hangul slug
- **WHEN** an authenticated workspace member opens a wiki detail URL whose Hangul slug is percent-encoded
- **THEN** the system displays the matching wiki page in that workspace

#### Scenario: Already-decoded mixed slug
- **WHEN** an authenticated workspace member opens a wiki detail URL whose ASCII and Hangul slug is already decoded
- **THEN** the system displays the matching wiki page in that workspace

#### Scenario: ASCII slug compatibility
- **WHEN** an authenticated workspace member opens a wiki detail URL with an ASCII-only slug
- **THEN** the system displays the same matching wiki page as before

### Requirement: Safe malformed-slug handling
The system SHALL handle a malformed percent-encoded wiki route slug without returning a server error or exposing page data. It MUST present the existing generic not-found state for an unresolvable or inaccessible page.

#### Scenario: Malformed percent encoding
- **WHEN** a user opens a wiki detail URL whose slug contains malformed percent encoding
- **THEN** the system returns the generic wiki not-found state without a 500 response

#### Scenario: Cross-workspace isolation
- **WHEN** a slug resolves to a page outside the active workspace or the requester lacks membership
- **THEN** the system does not reveal that page and returns the generic protected-route outcome

## Purpose

개발자가 로컬 개발 서버에서 실제 워크스페이스의 검색 파이프라인을 질의 단위로 조회해, 4채널 원시 결과와 RRF 융합 랭킹을 눈으로 검증할 수 있게 한다.

## ADDED Requirements

### Requirement: Development-only retrieval debug route

The system SHALL provide a retrieval debug route tree under an authenticated workspace that is available only while the dashboard runs in the development environment. It MUST render the route tree as not found in any non-development environment, independent of middleware routing configuration.

#### Scenario: Developer opens the debug route in a local dev server
- **WHEN** a developer opens the retrieval debug route on a dashboard server running in the development environment
- **THEN** the system renders the debug viewer without any additional gate beyond normal workspace authentication

#### Scenario: A deployed environment receives a request for the debug route
- **WHEN** a request targets the retrieval debug route on a dashboard server not running in the development environment
- **THEN** the system returns the normal not-found outcome without rendering the debug viewer or issuing a retrieval request

### Requirement: Authenticated live-workspace retrieval query

The system SHALL query the requesting member's own workspace through the existing authenticated retrieval endpoint, honoring the same session and tenant boundaries as every other authenticated workspace route. It MUST NOT bypass row-level security or use an elevated service credential to perform the query.

#### Scenario: Developer submits a query
- **WHEN** an authenticated workspace member submits a query and a result count on the debug viewer
- **THEN** the system requests retrieval evidence for that member's own workspace using that member's session, and displays the returned evidence

### Requirement: Per-channel evidence and fused ranking display

The system SHALL display, for a submitted query, each channel's raw returned results and the final RRF-fused ranking with each result's per-channel contribution scores. It MUST derive any total or summary score shown from the per-channel contribution values rather than assuming the retrieval response carries a precomputed total.

#### Scenario: Developer reviews channel results and fused ranking
- **WHEN** a retrieval query returns evidence spanning more than one channel
- **THEN** the viewer shows each channel's raw ranked results separately and a combined ranking ordered by each item's summed per-channel contribution

#### Scenario: A channel returns no results or fails
- **WHEN** the retrieval response reports a channel as unavailable or returning zero results
- **THEN** the viewer shows that channel's state instead of silently omitting it from the display

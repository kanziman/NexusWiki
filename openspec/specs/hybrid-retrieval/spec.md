# hybrid-retrieval Specification

## Purpose

한국어 중심 프로젝트 지식을 원문·위키의 의미·어휘 신호와 위키 링크 구조에서 함께 찾고, 일부 채널 장애에도 근거와 품질 메타데이터를 안정적으로 반환한다.

## Requirements

### Requirement: Four-channel retrieval with optional graph wave
The system SHALL retrieve from source-vector, wiki-vector, source-lexical, and wiki-lexical channels concurrently and fuse those results into the final ranking. Wiki-link graph expansion SHALL run as a second wave only when the versioned retrieval policy enables it, and the default policy MUST keep it disabled.

#### Scenario: All retrieval channels are available
- **WHEN** a workspace member submits a valid query under the default policy
- **THEN** the system returns a final evidence ranking derived from the four channels and reports the graph channel as disabled in metadata without calling it

#### Scenario: A policy enables graph expansion
- **WHEN** the retrieval policy enables the graph wave
- **THEN** the system expands bounded wiki-link evidence from the fused seeds and fuses it into the final ranking

### Requirement: Rank-based configurable fusion
The system SHALL fuse channel results by rank rather than comparing channel-specific raw scores, and SHALL keep per-channel weights, depth, candidate counts, and output limits in an explicit retrieval policy.

#### Scenario: Channels return incomparable score ranges
- **WHEN** semantic and lexical channels return results with different score scales
- **THEN** the fusion order depends on rank and configured channel weight rather than raw score magnitude

### Requirement: Tenant-filtered vector retrieval
Vector retrieval MUST apply the workspace boundary inside the ranked query and MUST use a bounded iterative search policy capable of satisfying the requested candidate count without exposing another workspace's rows.

#### Scenario: Nearest global vectors belong to another workspace
- **WHEN** a member searches a workspace whose nearest global vectors are owned by another workspace
- **THEN** the system searches within the authorized workspace boundary and returns no foreign vector evidence

### Requirement: Bounded graph expansion
Graph retrieval MUST enforce maximum depth, fan-out, and cycle protection, and SHALL remain independently disableable when its quality contribution has not been established.

#### Scenario: Wiki graph contains a cycle or high-degree node
- **WHEN** graph expansion reaches a cycle or a node beyond the configured fan-out
- **THEN** the system stops the affected traversal within the configured bounds

### Requirement: Retrieval channel fault isolation
Failure of one retrieval channel MUST NOT fail the entire query when another evidence channel succeeds, and the response metadata MUST identify the failed or disabled channel.

#### Scenario: One lexical channel fails
- **WHEN** a lexical retrieval channel returns an error while other channels succeed
- **THEN** the system excludes that channel, returns fused evidence from the successful channels, and reports the partial failure in metadata

### Requirement: Retrieval contribution observability
The system SHALL report each channel's contribution and whether it returned fewer candidates than requested so quality and latency regressions can be evaluated against a pinned golden set.

#### Scenario: Channel underfills its candidate request
- **WHEN** a retrieval channel returns fewer candidates than its configured request count
- **THEN** the result metadata records the requested count, returned count, latency, and contribution to final evidence

### Requirement: Membership gate before paid retrieval work
The retrieval route MUST verify the requester's JWT and workspace membership before it calls the query-embedding boundary. A request that fails the gate MUST NOT cause a provider call and MUST NOT create a usage event in any workspace.

#### Scenario: A non-member queries another workspace
- **WHEN** an authenticated user who is not a member of the workspace calls the retrieval route for it
- **THEN** the response is 403 with the fixed forbidden body, the embedding boundary is not called, and that workspace gains no usage event

#### Scenario: The bearer token is forged or expired
- **WHEN** the route is called with a token that the database layer rejects as an invalid JWT
- **THEN** the response is 401 rather than a server error, the embedding boundary is not called, and no workspace gains a usage event

#### Scenario: A member queries their workspace
- **WHEN** a member of any role calls the retrieval route with a valid query
- **THEN** the route proceeds to retrieval and returns evidence

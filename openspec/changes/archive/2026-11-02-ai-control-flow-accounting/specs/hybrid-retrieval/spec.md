## RENAMED Requirements

- FROM: `### Requirement: Five-channel two-wave retrieval`
- TO: `### Requirement: Four-channel retrieval with optional graph wave`

## MODIFIED Requirements

### Requirement: Four-channel retrieval with optional graph wave
The system SHALL retrieve from source-vector, wiki-vector, source-lexical, and wiki-lexical channels concurrently and fuse those results into the final ranking. Wiki-link graph expansion SHALL run as a second wave only when the versioned retrieval policy enables it, and the default policy MUST keep it disabled.

#### Scenario: All retrieval channels are available
- **WHEN** a workspace member submits a valid query under the default policy
- **THEN** the system returns a final evidence ranking derived from the four channels and reports the graph channel as disabled in metadata without calling it

#### Scenario: A policy enables graph expansion
- **WHEN** the retrieval policy enables the graph wave
- **THEN** the system expands bounded wiki-link evidence from the fused seeds and fuses it into the final ranking

## ADDED Requirements

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

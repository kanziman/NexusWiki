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

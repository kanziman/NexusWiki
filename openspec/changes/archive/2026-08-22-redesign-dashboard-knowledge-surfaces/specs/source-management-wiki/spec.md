## ADDED Requirements

### Requirement: Tenant-scoped source detail composition
The system MUST compose source detail data through the requester's authenticated session and workspace scope. The source record, chunks, and citing wiki pages MUST remain subject to Postgres RLS, and an inaccessible source MUST produce the same generic not-found presentation as an unknown source.

#### Scenario: Member views a source in the active workspace
- **WHEN** an authenticated member opens a source detail route for the active workspace
- **THEN** the system returns only the source, chunks, and citing wiki pages visible to that requester in that workspace

#### Scenario: Member requests an inaccessible source
- **WHEN** a source identifier belongs to another workspace or the requester lacks membership
- **THEN** the system reveals neither source metadata nor related chunk or wiki data and displays the generic source not-found state

#### Scenario: Related data is partially unavailable
- **WHEN** the source is visible but its chunk or wiki relationship query yields no visible rows
- **THEN** the system still displays the visible source and treats each unavailable related collection as empty

#### Scenario: Source detail query fails
- **WHEN** the source, chunk, or wiki relationship query returns an operational error rather than a successful empty result
- **THEN** the system displays a generic load-failure state instead of presenting the failed data as an empty collection

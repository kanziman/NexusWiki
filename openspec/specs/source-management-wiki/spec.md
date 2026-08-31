# source-management-wiki Specification

## Purpose

워크스페이스 멤버가 원본 소스(PDF/MD/TXT)를 수집 및 관리하고, 5단계 파이프라인 진행 상태를 추적하며, 컴파일된 위키 문서를 읽고 원문 출처를 역추적(이중 Citation)할 수 있는 RLS-scoped 소스 관리 및 위키 리더 기능을 제공한다.

## Requirements

### Requirement: Multi-format source dropzone and ingestion
The system SHALL accept source ingestion in 3 allowed MIME types (PDF, Plain Text, Markdown) up to 20 MiB per file with asynchronous job queueing.

#### Scenario: User uploads allowed document
- **WHEN** a member drops or submits a valid PDF, Markdown, or text file under 20 MiB
- **THEN** the system accepts the source and returns a job tracking identifier

#### Scenario: User submits oversized or unsupported file
- **WHEN** a member submits an unsupported file format or file exceeding 20 MiB
- **THEN** the system rejects the upload with descriptive error guidance

### Requirement: Real-time source job pipeline tracking
The system SHALL display pipeline progress for each source across the 5 background job stages (parse, compile, link_sync, embed, conflict_check).

#### Scenario: Member views processing source
- **WHEN** a source is currently being processed
- **THEN** the system displays the active stage and status indicator in the JobStepper

### Requirement: Source library with MIME type filter tabs
The system SHALL provide a source library view with 3 MIME filter tabs ('전체', 'PDF', '텍스트/마크다운') that filter the displayed sources by their file format.

#### Scenario: Member filters sources by MIME tab
- **WHEN** a member selects the 'PDF' filter tab
- **THEN** the source library displays only sources with PDF mime type

### Requirement: Read-only compiled wiki document reader
The system SHALL render compiled wiki markdown in a read-only document view with verification status callouts (verified, partial, unverified, disputed) and prevent direct editing.

#### Scenario: Member views verified wiki page
- **WHEN** a member opens a verified wiki document
- **THEN** the system displays the read-only banner, the verified status badge, and the structured markdown content

### Requirement: WikiLink resolution and unresolved red-link guidance
The system SHALL parse `[[WikiLink]]` tokens, resolve existing pages into navigable links, and render unresolved links as interactive RedLinkCta components.

#### Scenario: Member clicks resolved wiki link
- **WHEN** a member clicks a resolved wiki link
- **THEN** the system navigates to the target wiki page

#### Scenario: Member clicks unresolved red link
- **WHEN** a member clicks an unresolved red link
- **THEN** the system displays the creation prompt prefilled with the link's slug

### Requirement: Dual citation navigation and raw source anchor inspection
The system SHALL parse citation anchors (`[[wiki:...]]`, `[[src:...]]`) and open the source inspection side panel displaying the raw chunk content and character offsets when clicked.

#### Scenario: Member inspects raw source citation
- **WHEN** a member clicks a source citation chip
- **THEN** the system opens the citation drawer displaying the original source chunk text and coordinates

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

### Requirement: Owner-only raw source permanent deletion
The system SHALL allow workspace owners to permanently delete a raw source document and MUST cascade the deletion to its associated chunks and search embeddings while removing any stored object from storage.

#### Scenario: Owner deletes raw source
- **WHEN** an authenticated workspace owner requests permanent deletion of a raw source
- **THEN** the system deletes the raw source record, cascades deletion to all associated source chunks and embeddings, purges the storage object if present, and returns a success response

#### Scenario: Non-owner member attempts to delete raw source
- **WHEN** an authenticated workspace member without owner privileges requests deletion of a raw source
- **THEN** the system rejects the deletion request with a 403 Forbidden error and leaves the source data intact

#### Scenario: Deleting non-existent or foreign workspace source
- **WHEN** a deletion request targets a source that does not exist or belongs to another workspace
- **THEN** the system returns a 404 Not Found error without exposing source existence

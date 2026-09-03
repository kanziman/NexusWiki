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
The system SHALL provide a source library view with 3 MIME filter tabs ('전체', 'PDF', '텍스트/마크다운') that filter the displayed sources by their file format. Each tab SHALL carry the count of sources it would show. The filter tabs and the library search input SHALL be presented on one aligned toolbar row so that their top and bottom edges coincide rather than sitting at differing heights. Filter selection SHALL remain exposed to assistive technology through tab semantics and a selected state, not through visual styling alone.

#### Scenario: Member filters sources by MIME tab
- **WHEN** a member selects the 'PDF' filter tab
- **THEN** the source library displays only sources with PDF mime type

#### Scenario: Member reads how many sources a filter holds
- **WHEN** a member views the source library toolbar with sources of mixed formats registered
- **THEN** each filter tab shows the number of sources that filter would display, and those counts match the loaded workspace sources

#### Scenario: Assistive technology user selects a filter
- **WHEN** a screen reader user moves through the source library filter controls
- **THEN** each control is announced as a tab with an accessible name and a selected or unselected state

### Requirement: Source pipeline summary metrics
The system SHALL present a summary of the source library's processing health above the list, covering the total number of registered sources with their format breakdown, the number of chunks produced, the proportion of sources cited by at least one wiki page, and whether every registered source has completed chunking. Each summary figure SHALL be derived from the same workspace data the list itself renders, so that a figure never contradicts the rows below it. The summary SHALL state each figure in text rather than conveying it through color alone, and SHALL be omitted when the workspace has no sources.

When a chunk or wiki-citation aggregate query returns an operational error rather than a successful empty result, the system MUST NOT present the failed aggregate as a factual figure or as an assertion about the workspace. Each figure and row value that depends on the failed aggregate SHALL instead report that the aggregate could not be loaded, while values that do not depend on it remain shown.

#### Scenario: Member opens a source library with processed sources
- **WHEN** a member opens the source library for a workspace holding registered sources
- **THEN** the summary reports the total source count with its format breakdown, the total chunk count, the cited-source proportion, and the chunking completion state, each matching the loaded workspace sources

#### Scenario: Workspace has sources that no wiki page cites
- **WHEN** one or more registered sources are cited by no wiki page
- **THEN** the citation summary reports a proportion below full rather than presenting the workspace as fully linked

#### Scenario: A summary aggregate query fails
- **WHEN** the wiki-citation aggregate query returns an operational error while the source list itself loads
- **THEN** the citation figure and every row's citation value report that the aggregate could not be loaded, rather than showing a zero citation rate or asserting that sources are uncited, and the source count and format breakdown remain shown

#### Scenario: Workspace has no sources yet
- **WHEN** a member opens the source library for a workspace with no registered sources
- **THEN** the summary is not shown and the empty-state ingestion surface is presented instead

### Requirement: Uniform source list rows independent of citation count
The system SHALL render source library rows at a consistent height regardless of how many wiki pages cite a source. A row that would exceed the available width for citation links SHALL show a bounded number of them plus an indication of how many remain, rather than growing taller. Every row SHALL keep its column values aligned to the same column axes as the list header. On narrow viewports the list SHALL reflow without forcing horizontal scrolling of the page.

#### Scenario: Member views a source cited by many wiki pages
- **WHEN** a source is cited by more wiki pages than the row can display
- **THEN** the row shows a bounded number of citation links plus a remainder indicator, and its height matches rows for sources with fewer citations

#### Scenario: Member scans the list header against a row
- **WHEN** a member compares the list header labels with the values in any row
- **THEN** each value sits on the same column axis as the header label that names it

#### Scenario: Member opens the source library on a narrow viewport
- **WHEN** a member opens the source library on a narrow viewport
- **THEN** the rows reflow to fit without requiring horizontal scrolling of the page

### Requirement: Source row identity and upload recency
The system SHALL present, for every source library row, the source format, its title as a link to the source detail route, its stored size where known, its ingestion type, and when it was uploaded. Upload time SHALL be readable both as elapsed time and as an absolute date, so that recency and exact provenance are both recoverable without opening the source.

#### Scenario: Member scans a source row for provenance
- **WHEN** a member views a row for a source with a known byte size
- **THEN** the row shows the format, the linked title, the size, the ingestion type, and the upload time as both elapsed time and an absolute date

#### Scenario: Source has no recorded size
- **WHEN** a source has no recorded byte size
- **THEN** the row omits the size without displaying a placeholder value and still shows the remaining provenance fields

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
The system SHALL allow workspace owners to request permanent deletion of an unreferenced raw source document, MUST reject deletion while durable wiki, publication, Ask citation, or active pipeline references remain, and MUST durably schedule removal of any stored object before acknowledging the request.

#### Scenario: Owner deletes raw source
- **WHEN** an authenticated workspace owner requests permanent deletion of a raw source with no durable citation or active pipeline references
- **THEN** the system atomically deletes the raw source record, cascades deletion to associated source chunks and search embeddings, durably schedules any stored object for removal, and returns a 202 Accepted response

#### Scenario: Storage cleanup is retried
- **WHEN** a scheduled stored-object deletion encounters a transient Storage failure
- **THEN** the system retains a retryable cleanup job and does not report the cleanup job as completed until the object is removed or confirmed absent

#### Scenario: Owner requests deletion of a referenced raw source
- **WHEN** a raw source is referenced by a wiki page, public publication snapshot, saved Ask citation, or active pipeline job
- **THEN** the system rejects deletion with a 409 Conflict response carrying the `source_in_use` detail token and preserves the source, chunks, stored object, and references

#### Scenario: Non-owner member attempts to delete raw source
- **WHEN** an authenticated workspace member without owner privileges requests deletion of a raw source
- **THEN** the system rejects the deletion request with a 403 Forbidden error and leaves the source data intact

#### Scenario: Deleting non-existent or foreign workspace source
- **WHEN** a deletion request targets a source that does not exist or belongs to another workspace
- **THEN** the system returns a 403 Forbidden error without exposing source existence

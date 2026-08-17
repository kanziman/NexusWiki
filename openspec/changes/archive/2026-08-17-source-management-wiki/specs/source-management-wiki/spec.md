## ADDED Requirements

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

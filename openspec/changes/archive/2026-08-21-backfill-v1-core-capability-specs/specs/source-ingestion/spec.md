## Purpose

사용자가 파일, URL 또는 텍스트를 안전하게 등록하고 장시간 처리와 중복·추출 실패를 명확히 이해할 수 있도록 수집 경계와 결과 계약을 정의한다.

## ADDED Requirements

### Requirement: Asynchronous source registration
The system SHALL accept supported file, URL, and text sources without running the full ingestion pipeline inside the request, and SHALL return an accepted result containing the source and job identifiers.

#### Scenario: User submits a supported source
- **WHEN** an authorized workspace member submits a valid file, URL, or text source
- **THEN** the system returns an accepted response promptly and makes the queued processing job identifiable

### Requirement: Explicit duplicate outcome
The system MUST detect a source whose normalized content already exists in the workspace, MUST avoid creating duplicate derived records, and MUST return a distinguishable duplicate outcome.

#### Scenario: Same content is submitted again
- **WHEN** a member submits content whose normalized content hash already exists in the workspace
- **THEN** the system reports that the source was already collected and does not grow source, chunk, page, or embedding records

### Requirement: Original file retention
The system SHALL preserve the immutable original bytes of an accepted file source under a workspace- and source-scoped object identity so the source can be downloaded or reprocessed later.

#### Scenario: File source is accepted
- **WHEN** a file source registration succeeds
- **THEN** the original file is retained within the submitting workspace's private storage boundary

### Requirement: Extraction quality failure
The system MUST reject extracted document content that falls below the configured quality threshold, mark the processing result as requiring OCR, and expose a safe actionable failure reason.

#### Scenario: PDF yields insufficient text
- **WHEN** a submitted document produces too little usable text during extraction
- **THEN** the processing job ends with a `needs_ocr` outcome and the UI can explain that OCR or a better source is required

### Requirement: Traceable source chunks
The system SHALL preserve source chunk coordinates such that each stored chunk can be reproduced exactly from the extracted source text.

#### Scenario: Citation opens a source chunk
- **WHEN** a downstream citation refers to a source chunk and its character range
- **THEN** slicing the extracted source by that range yields exactly the stored chunk content

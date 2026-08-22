## ADDED Requirements

### Requirement: Source detail knowledge trace
The system SHALL provide a source detail destination that combines source identity and format metadata with its processing progress, extracted full text, ordered chunk coordinates, and citing wiki pages. It MUST provide a labelled return path to the source library and direct workspace-scoped routes to citing wiki pages.

#### Scenario: Member opens a source from the library
- **WHEN** a workspace member activates a source title or its detail action
- **THEN** the system opens that source's detail destination with source metadata, processing context, extracted content, chunks, and citing wiki relationships

#### Scenario: Member inspects a source chunk
- **WHEN** the member selects an available chunk in the source detail destination
- **THEN** the system displays that chunk's content, ordinal, and character start and end coordinates and permits copying the displayed text

#### Scenario: Source has no extracted content or citations
- **WHEN** the selected source has no available chunk, full-text content, or citing wiki page
- **THEN** the detail destination presents an explicit empty state for the unavailable region without fabricating processing success or citation relationships

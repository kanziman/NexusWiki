## MODIFIED Requirements

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

## ADDED Requirements

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

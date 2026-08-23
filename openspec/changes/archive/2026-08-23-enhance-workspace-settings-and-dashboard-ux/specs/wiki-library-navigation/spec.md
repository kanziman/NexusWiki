## MODIFIED Requirements

### Requirement: Wiki page context and navigation
The system SHALL present a wiki detail header containing a workspace-scoped navigation path with a direct back link to the library, page title, category, and verification context before the document body. The detail view SHALL expose navigable in-page headings when headings are available, clean any trailing redundant related-documents section from the body, and present resolved outgoing wiki links as an interactive related-documents card grid after the body.

#### Scenario: Member understands a document before reading
- **WHEN** a workspace member opens a wiki detail page
- **THEN** the page displays its navigation path with back link, title, category, and current verification or dispute context before the main content

#### Scenario: Document heading navigation is available
- **WHEN** a wiki page contains recognizable section headings
- **THEN** the detail view provides accessible links that navigate to those headings within the document without including trailing related-documents sections in the TOC

#### Scenario: Related documents are available
- **WHEN** a wiki page has resolved outgoing wiki links
- **THEN** the detail view displays those links after the document body as an interactive card grid linking to the related pages

#### Scenario: Document has no headings or related links
- **WHEN** a wiki page contains no recognizable section headings or resolved outgoing wiki links
- **THEN** the detail view omits the corresponding navigation region without leaving an empty container

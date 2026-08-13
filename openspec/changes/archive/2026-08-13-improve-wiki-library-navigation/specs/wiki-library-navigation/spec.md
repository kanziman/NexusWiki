## Purpose

워크스페이스 멤버가 컴파일된 위키 문서를 빠르게 찾고, 신뢰 상태와 연결된 문맥을 이해하며, 긴 문서를 읽기 쉽게 탐색하도록 한다.

## ADDED Requirements

### Requirement: Searchable wiki library
The system SHALL present workspace wiki pages as a document library that exposes the total visible document count, each page's title, category, verification state, and a bounded content preview. Members SHALL be able to narrow the loaded library by a case-insensitive text query and by category without exposing pages outside their workspace.

#### Scenario: Member finds a page by title or preview text
- **WHEN** a workspace member enters text that matches a loaded page title or content preview
- **THEN** the library displays only the matching workspace pages and retains a direct link to each page detail route

#### Scenario: Member filters the library by category
- **WHEN** a workspace member selects a category filter
- **THEN** the library displays only loaded workspace pages in that category and exposes the active filter accessibly

#### Scenario: Search has no matching pages
- **WHEN** the member's active query and category filter match no loaded pages
- **THEN** the library presents a clear no-results state without implying that no wiki pages exist in the workspace

### Requirement: Wiki page context and navigation
The system SHALL present a wiki detail header containing a workspace-scoped navigation path, page title, category, and verification context before the document body. The detail view SHALL expose navigable in-page headings when headings are available and SHALL present resolved outgoing wiki links as related documents after the body.

#### Scenario: Member understands a document before reading
- **WHEN** a workspace member opens a wiki detail page
- **THEN** the page displays its navigation path, title, category, and current verification or dispute context before the main content

#### Scenario: Document heading navigation is available
- **WHEN** a wiki page contains recognizable section headings
- **THEN** the detail view provides accessible links that navigate to those headings within the document

#### Scenario: Related documents are available
- **WHEN** a wiki page has resolved outgoing wiki links
- **THEN** the detail view displays those links after the document body as direct routes to the related pages

#### Scenario: Document has no headings or related links
- **WHEN** a wiki page contains no recognizable section headings or resolved outgoing wiki links
- **THEN** the detail view omits the corresponding navigation region without leaving an empty container

### Requirement: Responsive and accessible wiki navigation
The system SHALL preserve keyboard navigation, visible focus indication, and readable text hierarchy for the library controls and detail navigation across narrow and wide viewports.

#### Scenario: Keyboard member uses library controls
- **WHEN** a keyboard user moves through the query input, category controls, and page links
- **THEN** each control has an accessible name and visible focus state and can be operated without a pointer

#### Scenario: Narrow viewport member reads a detail page
- **WHEN** a member views a wiki detail page on a narrow viewport
- **THEN** the document context and available in-page navigation remain accessible without reducing the main body to an unreadable width

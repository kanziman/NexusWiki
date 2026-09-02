## ADDED Requirements

### Requirement: Floating bulk action bar for selected library pages
The system SHALL, when an authorized editor or owner has selected one or more loaded wiki pages, present bulk verify, bulk publish, and clear-selection actions in a floating action bar that does not displace the document list. The current-page select-all control SHALL remain in the list control row above the cards. Members without verification permission SHALL not see selection controls. Owner-only deletion controls SHALL remain gated to workspace owners.

#### Scenario: Authorized member selects library pages
- **WHEN** an authorized editor or owner selects one or more loaded wiki pages in the library
- **THEN** the system shows bulk verify, bulk publish, and clear-selection actions in a floating bar and does not push the document list downward

#### Scenario: Member without verification permission views the library
- **WHEN** a workspace viewer opens the wiki library
- **THEN** the system does not expose select-all, per-row selection, or bulk verify and bulk publish controls

#### Scenario: Member clears the current selection
- **WHEN** an authorized member activates clear-selection while pages are selected
- **THEN** the system clears the selection and hides the floating bulk action bar

## MODIFIED Requirements

### Requirement: Searchable wiki library
The system SHALL present workspace wiki pages as a document library titled as the wiki library that exposes the total visible document count, a workspace-scoped verification rate, per-category document counts, and each page's title, category, verification state, citation count, and a bounded content preview. Category filter labels SHALL match the home knowledge-grid mapping (`concepts` 개념, `entities` 엔티티, `guides` 가이드, `maps` 맵). Members SHALL be able to narrow the loaded library by a case-insensitive text query and by category, including from the per-category summary, without exposing pages outside their workspace. Each category filter SHALL display its document count.

#### Scenario: Member finds a page by title or preview text
- **WHEN** a workspace member enters text that matches a loaded page title or content preview
- **THEN** the library displays only the matching workspace pages and retains a direct link to each page detail route

#### Scenario: Member filters the library by category
- **WHEN** a workspace member selects a category filter
- **THEN** the library displays only loaded workspace pages in that category, exposes the active filter accessibly, and shows that category's document count on the filter

#### Scenario: Search has no matching pages
- **WHEN** the member's active query and category filter match no loaded pages
- **THEN** the library presents a clear no-results state without implying that no wiki pages exist in the workspace

#### Scenario: Member reads library knowledge-health counts
- **WHEN** a workspace member opens the wiki library of a workspace that has compiled pages across categories
- **THEN** the library shows the total document count, the verification rate for loaded pages, and a per-category document count that matches the loaded workspace pages

#### Scenario: Member filters from the category summary
- **WHEN** a workspace member activates a category in the knowledge-health summary
- **THEN** the library narrows to that category the same way the category filter does

### Requirement: Clean wiki library previews
The system SHALL derive each wiki library preview as bounded plain text that removes heading, emphasis, code, list, table, and WikiLink control syntax while preserving the human-readable document wording. Each library row SHALL present that preview on a compact card surface with a two-line clamp and a readable measure that does not stretch the excerpt across the full wide viewport. Search SHALL match the same cleaned wording that the member can see.

#### Scenario: Library page contains rich markdown
- **WHEN** a loaded wiki page contains markdown structure or aliased WikiLinks
- **THEN** its library row shows a bounded plain-text excerpt without exposing formatting delimiters or WikiLink brackets

#### Scenario: Member searches cleaned content
- **WHEN** the member enters wording that appears in the visible cleaned excerpt
- **THEN** the matching page remains in the filtered library results

#### Scenario: Library excerpt stays readable on a wide viewport
- **WHEN** a member views a library row whose cleaned excerpt is longer than two lines on a wide viewport
- **THEN** the excerpt is clamped to two lines and does not span the full wide canvas as a single unbounded line

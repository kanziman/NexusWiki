## ADDED Requirements

### Requirement: Bulk wiki page publication
The system SHALL allow authorized editors and workspace owners to publish multiple verified wiki pages in a single operation, creating or updating snapshots in `wiki_page_publications` for all eligible pages while skipping or reporting unverified, disputed, or expired pages.

#### Scenario: Editor bulk-publishes verified wiki pages
- **WHEN** an authorized editor or owner submits a bulk publication request for a list of verified wiki page IDs
- **THEN** the system creates or updates publication snapshots with current titles, content, and citations for all eligible pages and returns the list of published pages

#### Scenario: Bulk publication filters out unverified or disputed pages
- **WHEN** a bulk publication request includes wiki pages that are unverified, disputed, or expired
- **THEN** the system publishes only the eligible verified pages without failing the entire batch

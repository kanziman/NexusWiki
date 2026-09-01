## ADDED Requirements

### Requirement: Individual wiki page permanent deletion
The system SHALL provide an endpoint and user interface allowing an authorized workspace owner to permanently delete an individual wiki page, cascading deletion to associated chunks, embeddings, publication snapshots, and bookmarks, while forbidding deletion by non-owner roles.

#### Scenario: Owner deletes a wiki page
- **WHEN** an authenticated workspace owner requests deletion of a wiki page
- **THEN** the system permanently removes the wiki page and its dependent records (chunks, publications, bookmarks) from the database and navigates the user back to the wiki library

#### Scenario: Non-owner attempts wiki page deletion
- **WHEN** a non-owner member (editor or viewer) submits a request to delete a wiki page
- **THEN** the system rejects the deletion with a 403 Forbidden error and preserves the wiki page

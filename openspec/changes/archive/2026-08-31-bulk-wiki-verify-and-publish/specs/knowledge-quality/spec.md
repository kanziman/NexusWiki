## ADDED Requirements

### Requirement: Bulk wiki page verification
The system SHALL allow authorized editors and workspace owners to verify multiple wiki pages in a single operation, setting their `verification_status` to `verified` while recording the authenticated user's verification audit metadata and rejecting requests from users without the editor or owner role.

#### Scenario: Editor bulk-verifies multiple wiki pages
- **WHEN** an authorized editor or owner submits a bulk verification request for a list of wiki page IDs within the workspace
- **THEN** the system updates each page's `verification_status` to `verified`, sets `verified_by` to the requester's user ID, sets `verified_at` to the current timestamp, and returns the verified pages

#### Scenario: Non-editor attempts bulk verification
- **WHEN** a workspace viewer submits a bulk verification request
- **THEN** the system rejects the operation with a 403 Forbidden error and leaves all wiki pages unchanged

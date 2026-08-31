## ADDED Requirements

### Requirement: Owner-only raw source permanent deletion
The system SHALL allow workspace owners to permanently delete a raw source document and MUST cascade the deletion to its associated chunks and search embeddings while removing any stored object from storage.

#### Scenario: Owner deletes raw source
- **WHEN** an authenticated workspace owner requests permanent deletion of a raw source
- **THEN** the system deletes the raw source record, cascades deletion to all associated source chunks and embeddings, purges the storage object if present, and returns a success response

#### Scenario: Non-owner member attempts to delete raw source
- **WHEN** an authenticated workspace member without owner privileges requests deletion of a raw source
- **THEN** the system rejects the deletion request with a 403 Forbidden error and leaves the source data intact

#### Scenario: Deleting non-existent or foreign workspace source
- **WHEN** a deletion request targets a source that does not exist or belongs to another workspace
- **THEN** the system returns a 404 Not Found error without exposing source existence

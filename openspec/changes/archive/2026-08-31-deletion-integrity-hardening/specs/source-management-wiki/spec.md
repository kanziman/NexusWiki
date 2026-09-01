## MODIFIED Requirements

### Requirement: Owner-only raw source permanent deletion
The system SHALL allow workspace owners to request permanent deletion of an unreferenced raw source document, MUST reject deletion while durable wiki, publication, Ask citation, or active pipeline references remain, and MUST durably schedule removal of any stored object before acknowledging the request.

#### Scenario: Owner deletes raw source
- **WHEN** an authenticated workspace owner requests permanent deletion of a raw source with no durable citation or active pipeline references
- **THEN** the system atomically deletes the raw source record, cascades deletion to associated source chunks and search embeddings, durably schedules any stored object for removal, and returns a 202 Accepted response

#### Scenario: Storage cleanup is retried
- **WHEN** a scheduled stored-object deletion encounters a transient Storage failure
- **THEN** the system retains a retryable cleanup job and does not report the cleanup job as completed until the object is removed or confirmed absent

#### Scenario: Owner requests deletion of a referenced raw source
- **WHEN** a raw source is referenced by a wiki page, public publication snapshot, saved Ask citation, or active pipeline job
- **THEN** the system rejects deletion with a 409 Conflict response carrying the `source_in_use` detail token and preserves the source, chunks, stored object, and references

#### Scenario: Non-owner member attempts to delete raw source
- **WHEN** an authenticated workspace member without owner privileges requests deletion of a raw source
- **THEN** the system rejects the deletion request with a 403 Forbidden error and leaves the source data intact

#### Scenario: Deleting non-existent or foreign workspace source
- **WHEN** a deletion request targets a source that does not exist or belongs to another workspace
- **THEN** the system returns a 403 Forbidden error without exposing source existence

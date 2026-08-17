## ADDED Requirements

### Requirement: Workspace public settings sidecar and master killswitch
The system SHALL maintain a 1:1 `workspace_public_settings` sidecar with a master `allow_public_sharing` killswitch that enables or disables all public routes instantly for the workspace.

#### Scenario: Owner toggles public sharing killswitch
- **WHEN** the workspace owner enables or disables `allow_public_sharing`
- **THEN** the system updates the setting and controls anon visibility across all published pages

### Requirement: Verified-only wiki page publication sidecar
The system SHALL store human-approved wiki publications in `wiki_page_publications` and enforce that only pages with `verification_status = 'verified'` can be published.

#### Scenario: Member publishes a verified wiki page
- **WHEN** an editor or owner publishes a verified wiki page
- **THEN** the system creates or updates the publication record with the approved content and citations

#### Scenario: Attempt to publish an unverified wiki page
- **WHEN** an unverified or disputed wiki page is submitted for publication
- **THEN** the database trigger rejects the publication with an authorization error

### Requirement: Anonymous public wiki document viewer route
The system SHALL provide a `/p/[slug]/[page]` route accessible by unauthenticated users that renders published wiki markdown and citations when the master killswitch is active, and returns 404 otherwise.

#### Scenario: Anonymous user visits active published wiki page
- **WHEN** an anonymous user visits `/p/[workspace_slug]/[page_slug]` for a workspace with public sharing enabled
- **THEN** the system renders the published document with approved citations

#### Scenario: Anonymous user visits page when killswitch is disabled
- **WHEN** an anonymous user visits `/p/[workspace_slug]/[page_slug]` but `allow_public_sharing` is false
- **THEN** the system returns a 404 Not Found response

## ADDED Requirements

### Requirement: Wiki reader public publication controls
The system SHALL provide editor-or-owner controls on the wiki document reader to publish a verified page, copy its public URL, and unpublish it. Viewer members MUST NOT receive those controls. Unverified, partial, disputed, or expired pages MUST NOT be publishable from the reader.

#### Scenario: Editor publishes a verified wiki page from the reader
- **WHEN** an editor or owner publishes a verified wiki page from the document reader
- **THEN** the system stores a publication snapshot of the current title, content, slug, and citation sources and the reader switches to public-link copy and unpublish actions

#### Scenario: Editor copies the public link after publishing
- **WHEN** an editor or owner copies the public link of a published wiki page
- **THEN** the system copies `/p/[workspace_slug]/[page_slug]` for the current origin to the clipboard

#### Scenario: Editor unpublishes a wiki page from the reader
- **WHEN** an editor or owner unpublishes a wiki page from the document reader
- **THEN** the system deletes that page's publication record and the reader returns to the publish action

#### Scenario: Viewer or unverified page cannot publish
- **WHEN** a viewer opens the wiki reader, or an editor opens a page that is not currently verified
- **THEN** the system does not offer a working publish action for that page

### Requirement: Public viewer matches internal document typography
The public wiki document viewer SHALL render published markdown with the same heading, list, emphasis, code, table, and quote typography as the internal wiki reader. Wiki link markup MUST be shown as plain text. The public surface MUST NOT emit workspace-internal `/w/` links.

#### Scenario: Anonymous visitor reads a published page with markdown lists
- **WHEN** an anonymous user opens a published page whose content includes headings, lists, and emphasis
- **THEN** the system renders those structures as HTML typography rather than raw markdown, and does not link to internal wiki routes

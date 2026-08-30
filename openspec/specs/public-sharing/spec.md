# public-sharing Specification

## Purpose

검증 완료된 위키 문서를 외부 비로그인 사용자(`anon`)에게 안전하게 공개하고, `workspace_public_settings` 마스터 킬스위치를 통해 즉시 비공개로 전환할 수 있는 사이드카 아키텍처 기반 공개 공유 기능을 제공한다.

## Requirements

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

### Requirement: Public viewer three-column shell alignment
The public wiki document viewer SHALL render a header and a document body that share the same three column tracks on wide viewports, so the left navigation edge, the article column, and the table of contents edge stay vertically aligned. The public surface MUST NOT display an Ask input. Rendered UI MUST NOT contain emoji glyphs.

#### Scenario: Anonymous visitor opens a published page on a wide viewport
- **WHEN** an anonymous user opens a published page on a viewport wide enough for three columns
- **THEN** the header mark, the published-page navigation, and the article share one left edge, and the header actions and table of contents share one right edge

#### Scenario: Anonymous visitor sees no Ask surface
- **WHEN** an anonymous user opens a published page
- **THEN** the page does not render a question input, Ask submit control, or other guest prompt that would consume model tokens

### Requirement: Public viewer sidecar navigation and conversion
The public wiki document viewer SHALL list other publications from the same workspace using only the public publication sidecar, and SHALL link those documents exclusively to `/p/[workspace_slug]/[page_slug]`. Related publication cards MUST use the same public namespace. The viewer SHALL offer a conversion action to `/signup`. The public route MUST NOT query `wiki_pages`, `workspaces`, `raw_sources`, `source_chunks`, or `auth.users`.

#### Scenario: Anonymous visitor moves to another published page in the same workspace
- **WHEN** an anonymous user opens a published page in a workspace that has at least one other publication
- **THEN** the viewer lists that other publication by its published title and the link target is a `/p/` path for the same workspace slug

#### Scenario: Anonymous visitor starts from the public conversion action
- **WHEN** an anonymous user activates the public viewer's conversion action
- **THEN** the system navigates to `/signup`

#### Scenario: Public viewer emits no internal workspace links
- **WHEN** an anonymous user opens a published page that lists sibling publications
- **THEN** the page contains no `/w/` links

## ADDED Requirements

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

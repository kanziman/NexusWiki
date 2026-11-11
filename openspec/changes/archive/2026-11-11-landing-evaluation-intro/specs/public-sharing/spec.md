## ADDED Requirements

### Requirement: Public viewer returns to the public home
The public wiki document viewer SHALL expose the NexusWiki brand mark in its header as a link to the public home `/` with the accessible name "NexusWiki 홈". The link MUST NOT prefetch its target, so that merely opening a published page does not trigger the home route's authentication or database requests for visitors who carry a session. The link MUST be keyboard focusable with a visible focus state, and it MUST NOT change the header's three-column alignment.

#### Scenario: Visitor returns to the landing from a published page
- **WHEN** a visitor activates the brand mark in the public wiki viewer header
- **THEN** the system navigates to `/`, where an unauthenticated visitor sees the public landing

#### Scenario: Opening a published page does not prefetch the home route
- **WHEN** a visitor with a session cookie opens a published page
- **THEN** the home link does not prefetch `/` and the page emits no `/w/` links

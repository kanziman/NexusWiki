## ADDED Requirements

### Requirement: Active wiki section navigation
The system SHALL derive table-of-contents entries from supported document headings, preserve their nesting level, and indicate the section currently nearest the reading position. Selecting an entry SHALL scroll its matching heading into view and update the URL fragment without navigating away from the page.

#### Scenario: Member reads through document sections
- **WHEN** the member scrolls a wide-viewport wiki document across heading boundaries
- **THEN** the table of contents identifies the current section and retains the visual hierarchy of nested headings

#### Scenario: Member selects a table-of-contents entry
- **WHEN** the member activates a heading entry
- **THEN** the matching section scrolls into view and the current page URL records that heading fragment

#### Scenario: Document has no supported headings
- **WHEN** a wiki document contains no supported heading syntax
- **THEN** the reader does not present empty section links or an active-section indicator

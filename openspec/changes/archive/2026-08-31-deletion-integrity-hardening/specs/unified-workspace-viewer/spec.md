## MODIFIED Requirements

### Requirement: Citation click integrates with the viewer
The system SHALL route a citation marker activation in the conversation to the content viewer's matching tab and target, instead of opening a separate overlay panel, and MUST terminate loading with an explicit unavailable state when the cited resource was deleted or is inaccessible.

#### Scenario: Member clicks a wiki citation marker
- **WHEN** a member activates a resolved citation marker pointing at an accessible wiki page
- **THEN** the content viewer switches to the wiki document tab showing that page, and the conversation remains visible

#### Scenario: Member clicks a source citation marker
- **WHEN** a member activates a resolved citation marker pointing at an accessible raw source chunk
- **THEN** the content viewer switches to the raw source tab showing that source

#### Scenario: Member clicks an unavailable wiki citation marker
- **WHEN** a member activates a resolved wiki citation marker whose page was deleted or is inaccessible
- **THEN** the content viewer switches to the wiki tab and displays an explicit unavailable state without indefinite loading

#### Scenario: Member clicks an unavailable source citation marker
- **WHEN** a member activates a resolved source citation marker whose chunk was deleted or is inaccessible
- **THEN** the content viewer switches to the raw source tab and displays an explicit unavailable state without indefinite loading


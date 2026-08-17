## MODIFIED Requirements

### Requirement: Consistent workspace page structure
The system SHALL present every workspace destination with a consistent page frame containing a page title, contextual supporting information where applicable, and a readable content width. Primary actions and secondary controls SHALL use the same visual hierarchy across destinations. Where Wiki and Graph are presented as content-viewer tabs within the unified Ask destination rather than standalone destinations, each tab SHALL preserve this same page-frame consistency on switch.

#### Scenario: Member moves between workspace destinations
- **WHEN** a member navigates between Home, Sources, Ask, and Settings
- **THEN** each destination preserves a recognizable title, content frame, action hierarchy, and keyboard focus treatment

#### Scenario: Member switches content viewer tabs within Ask
- **WHEN** a member switches the content viewer between the wiki document, raw source, knowledge graph, and mind map tabs
- **THEN** each tab preserves a recognizable title, content frame, and keyboard focus treatment consistent with the other workspace destinations

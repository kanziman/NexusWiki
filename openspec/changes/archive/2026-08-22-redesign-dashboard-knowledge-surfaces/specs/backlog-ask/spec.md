## ADDED Requirements

### Requirement: Consistent backlog document hierarchy
The system SHALL present backlog topics using the same searchable document-table hierarchy as other workspace libraries while preserving topic selection and source-addition actions as distinct controls.

#### Scenario: Member scans and filters backlog topics
- **WHEN** the backlog contains unresolved topics and the member enters a search query
- **THEN** matching topic names, raw slugs, or referring wiki titles remain visible with impact and first-detected context in a readable row hierarchy

#### Scenario: Member operates a backlog row
- **WHEN** the member selects the topic control, a referring wiki link, or the source-addition action within one row
- **THEN** only the selected control's documented destination or panel opens, without the other row actions firing

### Requirement: Structured Ask answers with dual-citation legend
The system SHALL preserve supported markdown headings, lists, tables, block quotes, fenced and inline code, emphasis, and safe links in streamed Ask answer text while keeping server-resolved citation markers in their original text positions. It SHALL identify the visual distinction between raw-source and wiki-document citation markers. A link using an unsafe executable protocol MUST NOT become navigable.

#### Scenario: Resolved answer contains markdown and citations
- **WHEN** a completed streamed answer contains supported markdown with issued source and wiki citation aliases
- **THEN** the answer renders semantic markdown, retains clickable citation markers at the corresponding positions, and exposes which marker style denotes each evidence kind

#### Scenario: Answer is still streaming
- **WHEN** answer text arrives before the citations event resolves its aliases
- **THEN** citation placeholders remain non-interactive while the available markdown text stays readable

#### Scenario: Answer contains an unsafe markdown link
- **WHEN** answer text contains a markdown link whose target uses an executable or unsupported protocol
- **THEN** the answer preserves the link label as non-navigable text and does not expose an executable target

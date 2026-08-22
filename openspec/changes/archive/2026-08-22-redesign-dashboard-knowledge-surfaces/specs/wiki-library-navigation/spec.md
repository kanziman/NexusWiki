## ADDED Requirements

### Requirement: Clean wiki library previews
The system SHALL derive each wiki library preview as bounded plain text that removes heading, emphasis, code, list, table, and WikiLink control syntax while preserving the human-readable document wording. Search SHALL match the same cleaned wording that the member can see.

#### Scenario: Library page contains rich markdown
- **WHEN** a loaded wiki page contains markdown structure or aliased WikiLinks
- **THEN** its library row shows a bounded plain-text excerpt without exposing formatting delimiters or WikiLink brackets

#### Scenario: Member searches cleaned content
- **WHEN** the member enters wording that appears in the visible cleaned excerpt
- **THEN** the matching page remains in the filtered library results

### Requirement: Structured read-only wiki markdown
The system SHALL render compiled wiki content as semantic headings, paragraphs, ordered and unordered lists, tables, block quotes, fenced and inline code, emphasis, safe external links, and resolved or unresolved WikiLinks while preserving read-only governance and verification context. A link using an unsafe executable protocol MUST NOT become navigable.

#### Scenario: Member reads a structured wiki page
- **WHEN** compiled wiki content contains supported block and inline markdown
- **THEN** the reader presents the corresponding semantic document structure without exposing the formatting delimiters as ordinary text

#### Scenario: Wiki content contains internal links
- **WHEN** compiled content contains a resolved or unresolved WikiLink
- **THEN** the reader renders the resolved link as a workspace-scoped wiki route and the unresolved link as the existing source-ingestion guidance

#### Scenario: Wiki content contains an unsafe markdown link
- **WHEN** compiled content contains a markdown link whose target uses an executable or unsupported protocol
- **THEN** the reader preserves the link label as non-navigable text and does not expose an executable target

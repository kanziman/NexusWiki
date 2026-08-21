## Purpose

수집된 원문을 검증 가능한 읽기 전용 위키 페이지와 검색 자산으로 반복 생성하면서 링크, 식별자 및 재처리 결과의 일관성을 보장한다.

## ADDED Requirements

### Requirement: Validated structured compilation
The system SHALL compile extracted source content into structured wiki pages, MUST validate the generated structure before persistence, and SHALL retry recoverable validation failures with the failure details up to the configured attempt limit.

#### Scenario: First generated result violates the schema
- **WHEN** a compilation provider returns a structurally invalid result
- **THEN** the system feeds the validation errors into a bounded retry and persists only a valid result

#### Scenario: All compilation attempts fail validation
- **WHEN** every bounded compilation attempt remains invalid
- **THEN** the system persists no invalid wiki page and records a safe terminal job failure

### Requirement: Deterministic wiki identity
The system MUST derive each wiki page slug deterministically from its title, apply a versioned normalization rule, and resolve collisions against both existing pages and unresolved link targets without delegating slug ownership to the language model.

#### Scenario: Same normalized title is compiled repeatedly
- **WHEN** the same title is compiled again under the same slugging version
- **THEN** the system derives the same base slug and resolves any existing collision deterministically

### Requirement: WikiLink synchronization
The system SHALL synchronize wiki links from compiled page content and MUST retain unresolved targets as red links until a matching page exists.

#### Scenario: Compiled page references a missing target
- **WHEN** a compiled page contains a WikiLink whose target page does not exist
- **THEN** the system records an unresolved link that can drive navigation and backlog behavior

### Requirement: Dual searchable representations
The system SHALL maintain searchable representations for both original source chunks and compiled wiki content, including the tokenizer, chunker, and embedding version information required to detect incompatible data.

#### Scenario: Compilation and source processing complete
- **WHEN** a source reaches the searchable state
- **THEN** both source evidence and compiled wiki evidence are available to retrieval with their processing versions

### Requirement: Shrinking reprocessing cleanup
The system MUST remove stale chunks, embeddings, and links when reprocessing produces fewer derived units than a previous run.

#### Scenario: Reprocessed source becomes shorter
- **WHEN** a source or compiled page is reprocessed into fewer chunks or links
- **THEN** derived rows beyond the new result are removed and cannot appear in retrieval or navigation

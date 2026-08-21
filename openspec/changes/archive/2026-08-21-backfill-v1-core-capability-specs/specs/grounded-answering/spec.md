## Purpose

질문 응답이 검색된 근거만 인용하고 원문과 컴파일된 위키 양쪽으로 추적되며, 스트리밍 중에도 위조·무근거 인용을 사용자에게 사실처럼 제시하지 않도록 한다.

## ADDED Requirements

### Requirement: Server-issued evidence aliases
The system MUST issue short request-scoped aliases for retrieved source and wiki evidence before generation and MUST resolve only issued aliases back to durable evidence identifiers.

#### Scenario: Answer generator cites issued evidence
- **WHEN** generated text contains an alias issued for the current request
- **THEN** the system resolves the alias to the corresponding source or wiki evidence and its trace coordinates

### Requirement: Citation intersection and forgery removal
Returned citations MUST be the intersection of aliases parsed from the generated answer and aliases issued from retrieval, and the system MUST remove and count unissued aliases.

#### Scenario: Generator fabricates an alias
- **WHEN** generated text contains an alias that was not issued for the request
- **THEN** the system removes that marker, excludes it from citations, and increments the fabricated-anchor metric

### Requirement: Explicit no-evidence answer
The system MUST avoid an evidence-grounded provider answer when retrieval yields no usable evidence and SHALL return an explicit statement that supporting evidence was not found.

#### Scenario: Retrieval yields no evidence
- **WHEN** all retrieval channels produce no usable evidence for a question
- **THEN** the system returns `근거를 찾지 못했습니다.` with no fabricated citation

### Requirement: Source anchor injection defense
The system MUST strip citation-like control anchors embedded in collected source content before that content is chunked or included in an answer prompt.

#### Scenario: Collected document contains a forged citation marker
- **WHEN** a source includes text that resembles a system citation alias
- **THEN** the marker cannot become an issued citation or control the answer parser

### Requirement: Ordered answer streaming
The system SHALL stream answers over an authenticated POST response in the order `meta`, zero or more `delta`, `citations`, and `done`.

#### Scenario: Grounded streaming answer completes
- **WHEN** an authenticated member asks a question with usable evidence
- **THEN** the client receives metadata first, answer deltas next, resolved citations after the text, and one terminal done event

### Requirement: Contextual prompt and language behavior
The system SHALL allow an authorized visible Ask prompt template to be selected, SHALL fall back safely when a requested template is unavailable, and MUST answer in the language of the question.

#### Scenario: Member asks in Korean with an unavailable template
- **WHEN** a member submits a Korean question with a template identifier they cannot use
- **THEN** the system uses the default visible template and returns the answer in Korean

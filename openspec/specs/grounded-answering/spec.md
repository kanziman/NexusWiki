# grounded-answering Specification

## Purpose

질문 응답이 검색된 근거만 인용하고 원문과 컴파일된 위키 양쪽으로 추적되며, 스트리밍 중에도 위조·무근거 인용을 사용자에게 사실처럼 제시하지 않도록 한다.

## Requirements

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

### Requirement: Terminal outcome for failed answer streams
The system MUST finish every started Ask turn with a terminal state whenever the failure happens while the server can still write the turn. A malformed provider frame or a provider error frame during streaming MUST end the turn with the `llm_unavailable` error outcome in the `citations` event and MUST NOT persist partial generated text as a resolved answer. A failure while gathering evidence or preparing the prompt MUST also end the turn with an error outcome. A client that disconnects before the turn ends is outside this requirement and is tracked by issue #170.

#### Scenario: Provider stream contains a malformed frame
- **WHEN** the answer stream delivers a data frame that cannot be parsed
- **THEN** the client receives the error outcome and `done`, and the stored turn has status `error` rather than `streaming`

#### Scenario: Provider stream contains a frame with the wrong shape
- **WHEN** the answer stream delivers a parseable frame whose `choices`, `delta`, or `content` has an unexpected type
- **THEN** the client receives the error outcome and `done`, and the stored turn has status `error` rather than `streaming`

#### Scenario: Preparation fails after the turn started
- **WHEN** retrieval, evidence content lookup, template selection, or prompt rendering fails after the turn was started
- **THEN** the client receives an error outcome and `done`, the stored turn has status `error`, and the provider is not called

#### Scenario: Provider reports an error mid-stream
- **WHEN** the answer stream delivers a provider error frame after partial text
- **THEN** the stored turn has status `error`, contains no partial answer, and is not reported as resolved

### Requirement: Citation quality metrics exclude removed anchors
The system SHALL compute dual-citation and unsourced-sentence metrics from the answer after unissued anchors are removed, and SHALL persist the metrics with the turn without storing additional answer text. An anchor placed directly after sentence-ending punctuation MUST count toward the sentence it follows.

#### Scenario: A sentence cites only fabricated anchors
- **WHEN** a sentence's only anchors were not issued for the request
- **THEN** that sentence does not count as dual-cited and counts as unsourced

#### Scenario: Anchor follows the period
- **WHEN** generated text places a valid anchor immediately after the sentence's period
- **THEN** that sentence counts as cited

### Requirement: Partial retrieval is reported to the answer client
The system SHALL report retrieval channels that failed for the request in Ask metadata, and MUST NOT report a channel that is intentionally disabled by policy.

#### Scenario: One retrieval channel fails
- **WHEN** a channel fails while another channel returns evidence
- **THEN** the `meta` event names the failed channel and the client shows its partial-search notice

#### Scenario: Graph channel is disabled
- **WHEN** all enabled channels succeed and the graph channel is disabled by policy
- **THEN** the `meta` event reports no missing channels and no notice is shown

### Requirement: Ask 컨텍스트 토큰 예산과 이중 근거 쿼터
시스템은 Ask 프롬프트의 근거 블록을 조립할 때 설정된 컨텍스트 토큰 상한을 MUST 강제해야 한다. 검색 결과에 위키 근거와 원문 근거가 모두 포함되어 있을 때는 한 종류의 긴 문서가 다른 종류의 근거를 전부 밀어내지 못하도록 두 종류 모두 최소 1건 이상의 근거 블록과 별칭(`[[wiki:...]]`, `[[src:...]]`)을 프롬프트에 SHALL 보존해야 한다. 근거 융합(RRF) 시 동일 문서가 여러 채널에서 검색되면 채널별 메타데이터(`title`, `slug` 등)를 MUST 병합해 벡터 채널이 먼저 적중한 위키 근거도 제목과 슬러그를 잃지 않게 한다. 컨텍스트 예산 적용 결과(예산 토큰, 사용 토큰, 위키·원문 토큰, 잘림 여부)는 본문 없이 턴의 `control_report`에 SHALL 기록한다.

#### Scenario: 긴 위키 근거가 있어도 원문 근거가 함께 보존된다
- **WHEN** 검색 결과에 컨텍스트 예산을 초과하는 긴 위키 근거와 원문 근거가 함께 있다
- **THEN** 조립된 컨텍스트는 토큰 상한 안에서 잘리며 위키 별칭 블록과 원문 별칭 블록이 모두 최소 1건 이상 포함되고, `control_report`에 잘림 여부가 기록된다

#### Scenario: 위키가 검색 상위를 독차지해도 원문 근거가 프롬프트에 실린다
- **WHEN** 융합 결과의 상위 k개가 전부 위키이고 그 뒤에 원문 근거가 있다
- **THEN** 시스템은 위키와 원문을 절반씩 골라 컨텍스트를 조립하고, 한 종류가 모자라면 빈자리를 다른 종류로 채운다

#### Scenario: 한 종류 근거만 있을 때 남은 예산을 사용한다
- **WHEN** 검색 결과에 위키 근거만 있거나 원문 근거만 있다
- **THEN** 해당 종류 근거가 전체 컨텍스트 토큰 상한까지 사용할 수 있다

#### Scenario: 벡터 채널과 어휘 채널이 같은 위키 문서를 반환한다
- **WHEN** 벡터 채널이 메타데이터 없이 먼저 적중하고 어휘 채널이 같은 위키 문서의 `title`과 `slug`를 반환한다
- **THEN** 융합된 위키 근거는 `title`과 `slug`를 보존하여 컨텍스트 블록 제목과 Router `LOOKUP` 판정에 사용한다

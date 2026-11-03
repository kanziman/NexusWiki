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

### Requirement: Ask 인용 계약과 수리
시스템은 Ask 답변 스트림이 끝난 뒤 저장 전에 인용 계약을 SHALL 검증한다. 위조 앵커가 있거나, 답변이 있는데 해소된 인용이 하나도 없으면 위반이다. 답변 전체가 근거 부족을 밝히고 인용이 없으면 위반이 MUST NOT 된다. 근거 부족 문장과 단정이 섞이고 인용이 없는 답변은 위반이다. 위반이면 시스템은 위반 코드를 되먹여 공급자를 최대 1회 SHALL 다시 호출하며, 수리 결과는 기존 `citations.text` 교체로 전달하고 SSE 이벤트 순서를 MUST 유지한다. 수리 호출의 비용은 일반 호출과 같게 MUST 기록한다.

#### Scenario: 인용이 하나도 없는 답변을 수리한다
- **WHEN** 근거가 있는 턴의 답변에 해소된 인용이 없고 수리 호출이 발급 앵커를 포함한 답변을 돌려준다
- **THEN** `citations.text`가 수리된 답변으로 교체되고, 턴은 `resolved`로 저장되며, 공급자 호출은 2회다

#### Scenario: 근거 부족을 밝힌 답변
- **WHEN** 답변이 제공된 자료로 답할 수 없다고 밝히고 인용이 없다
- **THEN** 위반으로 세지 않고 수리 호출 없이 `resolved`로 저장한다

#### Scenario: 단정과 근거 부족이 섞인 답변
- **WHEN** 답변이 단정 문장과 근거 부족 문장을 함께 담고 인용이 없다
- **THEN** 위반으로 세어 수리한다

#### Scenario: 정상 답변
- **WHEN** 답변에 발급 앵커가 있고 위조 앵커가 없다
- **THEN** 공급자 호출은 1회이고 일부 문장에 인용이 없어도 수리하지 않는다

### Requirement: 결정론적 Ask Fallback
수리 후에도 계약을 어기거나 수리 호출이 실패하면, 시스템은 상위 근거를 나열한 결정론적 답변으로 턴을 SHALL 끝내고 `fallback` 상태로 저장한다. 이 답변의 앵커는 MUST 모두 그 턴에 발급된 것이어야 하고, 근거 본문에 든 앵커 문법은 MUST 제거된다. 클라이언트는 이 답변이 자동 검증된 근거 목록임을 SHALL 표시한다.

#### Scenario: 수리도 실패한다
- **WHEN** 수리 호출의 답변도 인용 계약을 어긴다
- **THEN** 턴 상태는 `fallback`이고, 답변의 모든 앵커가 발급 앵커이며, 공급자 호출은 2회를 넘지 않는다

#### Scenario: 수리 호출 자체가 실패한다
- **WHEN** 수리 호출이 공급자 오류로 끝난다
- **THEN** 턴은 `streaming`에 남지 않고 `fallback`으로 저장된다

#### Scenario: 근거 본문에 앵커 문법이 들어 있다
- **WHEN** Fallback에 쓰는 근거 본문이 `[[wiki:w9]]`를 담고 있다
- **THEN** 그 문법은 답변에 남지 않고 위조 앵커로 세지지 않는다

#### Scenario: 기록을 다시 연다
- **WHEN** 사용자가 `fallback` 턴이 있는 스레드를 다시 연다
- **THEN** 같은 안내와 근거 목록이 표시된다

### Requirement: 품질 통제 모드
시스템은 품질 통제를 `off`, `shadow`, `enforce` 모드로 SHALL 전환할 수 있어야 한다. `off`는 검증하지 않고, `shadow`는 위반을 기록만 하며 추가 호출을 MUST NOT 한다. `enforce`는 수리와 Fallback을 수행한다. 턴의 통제 보고서는 모드, 위반 코드, 수리 여부, Fallback 여부를 본문 없이 SHALL 담는다.

#### Scenario: shadow 모드의 위반
- **WHEN** `shadow`에서 인용 없는 답변이 나온다
- **THEN** 공급자 호출은 1회이고 턴은 `resolved`이며 통제 보고서에 위반 코드가 남는다

#### Scenario: off 모드
- **WHEN** `off`에서 인용 없는 답변이 나온다
- **THEN** 공급자 호출은 1회이고 통제 보고서의 위반 목록은 비어 있다

### Requirement: 분쟁 근거 표시
시스템은 분쟁 중인 위키 페이지를 근거로 쓸 때 모델 컨텍스트에 분쟁 중임을 SHALL 표시하고, `citations`에 해당 별칭을 담아 답변 화면이 경고를 표시하게 한다.

#### Scenario: 분쟁 페이지가 근거에 있다
- **WHEN** Ask 근거에 `disputed` 위키 페이지가 있다
- **THEN** 프롬프트의 그 블록에 분쟁 표시가 있고, `citations.disputed_aliases`에 별칭이 있으며, 화면에 경고가 표시된다

#### Scenario: 분쟁 페이지가 없다
- **WHEN** 근거에 분쟁 페이지가 없다
- **THEN** 프롬프트에 분쟁 표시가 없고 경고도 없다

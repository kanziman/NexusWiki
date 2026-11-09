# ask-replay-scorecard Specification

## Purpose

ask 합성 재생의 결과를 질문별 통과 여부, 지연 백분위, 실행 간 누적 기록, 눈으로 볼 수 있는 성적표로 바꿔, 코드나 모델을 바꿨을 때 어느 질문이 왜 떨어졌는지 사람이 따라갈 수 있게 한다.

## Requirements

### Requirement: Per-question pass verdict
The system SHALL assign every replayed question a pass or fail verdict with a single-line reason when it fails. An answerable question MUST pass only when all of the following hold: the turn completed normally, the answer contains zero fabricated anchors, the expected-fact check is not false, the answer states none of the question's forbidden facts, and the answer cites both a wiki page and a raw source at least once. A question whose expected-fact check is undefined MUST NOT fail on that criterion. A question with no forbidden facts defined MUST NOT fail on that criterion. A question marked unanswerable MUST pass only when it contains zero fabricated anchors and either the turn ended in the no-evidence outcome or the turn completed normally with an answer whose first body line, ignoring heading lines and whitespace differences, begins with the standard refusal statement the answer prompt instructs the model to use. A turn that never reached the model MUST fail with a reason naming its outcome.

#### Scenario: Answerable question meets every criterion
- **WHEN** an answerable question completes normally with zero fabricated anchors, a true expected-fact check, and at least one wiki and one raw-source citation
- **THEN** the verdict is pass and no failure reason is recorded

#### Scenario: Question fails on one criterion
- **WHEN** an answerable question completes normally but cites only wiki pages
- **THEN** the verdict is fail and the reason states that the dual citation is missing

#### Scenario: Several criteria fail at once
- **WHEN** an answerable question has fabricated anchors and a false expected-fact check
- **THEN** the verdict is fail and the single-line reason names the first failing criterion in a fixed documented order

#### Scenario: No expected fact defined
- **WHEN** an answerable question has no expected-fact list and meets every other criterion
- **THEN** the verdict is pass

#### Scenario: Answer states a forbidden fact
- **WHEN** an answerable question's answer contains its expected fact and also states one of its forbidden facts
- **THEN** the verdict is fail and the reason states that a forbidden fact was stated

#### Scenario: No forbidden facts defined
- **WHEN** an answerable question from the existing sample has no forbidden-fact list
- **THEN** the verdict is the same as it was before forbidden facts existed

#### Scenario: Unanswerable question correctly refused
- **WHEN** a question marked unanswerable ends in the no-evidence outcome with zero fabricated anchors
- **THEN** the verdict is pass even though it carries no citations

#### Scenario: Unanswerable question refused by the model after retrieval found unrelated evidence
- **WHEN** a question marked unanswerable completes normally with zero fabricated anchors and its first body line begins with the standard refusal statement
- **THEN** the verdict is pass even though the turn did not end in the no-evidence outcome

#### Scenario: Unanswerable question answered anyway
- **WHEN** a question marked unanswerable completes normally with an answer whose first body line does not begin with the standard refusal statement
- **THEN** the verdict is fail and the reason states that it should have been refused

#### Scenario: Refusal statement not at the start
- **WHEN** a question marked unanswerable completes normally and the standard refusal statement appears only after other body text
- **THEN** the verdict is fail because the answer is not a refusal

#### Scenario: Refusal with fabricated anchors
- **WHEN** a question marked unanswerable completes normally with a refusal first line but one or more fabricated anchors
- **THEN** the verdict is fail and the reason names the fabricated anchors

#### Scenario: Refusal wording differs only in spacing
- **WHEN** the refusal first line differs from the standard statement only by whitespace
- **THEN** the verdict treats it as the standard refusal

#### Scenario: Turn did not reach the model
- **WHEN** an answerable question ends in an HTTP error or the no-evidence outcome
- **THEN** the verdict is fail and the reason names that outcome

### Requirement: Latency percentiles in the run summary
The run summary SHALL include the p50 and p95 of per-question elapsed time computed over the questions that produced an elapsed time, and MUST report them as absent rather than zero when no question produced one.

#### Scenario: Percentiles over a normal run
- **WHEN** a run finishes with elapsed times for its questions
- **THEN** the summary reports p50 and p95 in the same unit as the recorded elapsed times

#### Scenario: No elapsed time recorded
- **WHEN** every question ended before an elapsed time was recorded
- **THEN** the summary reports both percentiles as absent

### Requirement: Cumulative scorecard record
The system SHALL append exactly one line per finished replay run to a scorecard file holding the run label, source revision, model, pass rate, question count, token totals, cost, and latency p50 and p95. Appending MUST NOT modify or remove earlier lines. A line MUST NOT contain any answer text, question text, credential, or provider identifier.

#### Scenario: Two runs recorded in order
- **WHEN** two replay runs finish one after another
- **THEN** the scorecard file holds both lines in run order and the first line is unchanged

#### Scenario: Run stopped early by the spend limit
- **WHEN** a run stops before all planned questions were asked
- **THEN** its line records the number asked and the number planned so it cannot be read as a full run

#### Scenario: Unknown revision or model
- **WHEN** the source revision or model cannot be determined
- **THEN** the line records them as unknown instead of omitting the run

### Requirement: Static scorecard page
The system SHALL generate a self-contained static HTML page from the scorecard file and the per-run result files that shows one row per run with pass rate, tokens, cost per question, and latency p50 and p95, and, for a selected run, a per-question table with each verdict and its failure reason. Failing questions MUST be visually distinguishable from passing ones by more than color alone. The page MUST state at the top that the figures come from a synthetic sample and are not production traffic, and MUST open from the filesystem without a server or network access.

#### Scenario: Several runs shown
- **WHEN** the scorecard file holds three runs
- **THEN** the page lists three rows in run order with the five run-level figures

#### Scenario: Run detail shown
- **WHEN** a viewer selects a run that has a result file
- **THEN** the page shows every question of that run with its verdict and, for failures, the one-line reason

#### Scenario: Run without a result file
- **WHEN** a scorecard line has no matching result file
- **THEN** the page still lists the run and marks its detail as unavailable

#### Scenario: Empty scorecard
- **WHEN** the scorecard file does not exist or is empty
- **THEN** the page states that no runs are recorded and names the command that produces one

#### Scenario: Untrusted text in results
- **WHEN** a result contains markup characters in an answer or reason
- **THEN** the page displays them as text and never executes them

### Requirement: Page generation spends nothing
Generating the scorecard page from existing result files SHALL NOT contact the API, the database, or any model provider, and MUST be runnable without the replay stack.

#### Scenario: Offline generation
- **WHEN** the page is generated while no replay stack is running and no network is available
- **THEN** generation succeeds and incurs no provider cost

### Requirement: Existing replay outputs remain compatible
The existing result file fields and the before/after comparison output SHALL remain unchanged in meaning; new fields MUST be additive.

#### Scenario: Older result file
- **WHEN** a result file written before this capability is compared or rendered
- **THEN** the comparison works as before and the page derives verdicts from the row fields it already holds

### Requirement: Retrieval-only scoring on the replay question set
The system SHALL score retrieval for the replay question set without generating answers, by calling the workspace retrieval endpoint with the requester's token for every question and comparing the returned evidence with the question's expected documents. A source evidence item MUST count as relevant only when it comes from an expected document. A wiki evidence item MUST count as relevant only when the wiki page lists an expected document among the raw sources it was compiled from. For each run the system SHALL report, over answerable questions, hit@1, hit@3, hit@8, mean reciprocal rank, source-only hit@8, wiki-only hit@8, and dual hit@8 (at least one relevant source item and one relevant wiki item within the top 8), and SHALL state next to the metrics that hit@k is the share of questions with at least one relevant item in the top k. Questions marked unanswerable MUST be excluded from those metrics and reported only by how many evidence items were returned. A question MUST be recorded as a measurement failure and counted as not found in every metric when its retrieval request fails, when the retrieval response reports any failed channel, when one of its expected documents cannot be mapped to a raw source in the workspace, or when a returned source item cannot be traced to its raw source; the run SHALL report measurement failures by kind. The number of expected documents of a multi-document question MUST come from the question definition so that failed questions stay in the multi-document counts. The run MUST refuse to start when two raw sources in the workspace share a title. The run MUST NOT call any answer-generation provider.

#### Scenario: Relevant source item ranked first
- **WHEN** the first returned evidence item is a source item from the expected document
- **THEN** the question counts toward hit@1, hit@3, hit@8 and contributes a reciprocal rank of 1

#### Scenario: Relevant wiki item through its compiled sources
- **WHEN** a returned wiki item's page lists the expected document among its compiled raw sources
- **THEN** that item counts as relevant even though it is not a source item

#### Scenario: Wiki page compiled from another document
- **WHEN** a returned wiki item's page lists only raw sources other than the expected documents
- **THEN** that item does not count as relevant

#### Scenario: No relevant item in the top 8
- **WHEN** none of the returned evidence items is relevant
- **THEN** the question counts against every hit@k and contributes a reciprocal rank of 0

#### Scenario: Only one side of the dual citation is found
- **WHEN** the top 8 contains a relevant source item but no relevant wiki item
- **THEN** the question counts toward hit@8 and source-only hit@8 but not toward dual hit@8

#### Scenario: Question with several expected documents
- **WHEN** a question expects two documents and the top 8 contains relevant items for only one of them
- **THEN** it counts as found under "any expected document" and not found under "every expected document"

#### Scenario: Unanswerable question
- **WHEN** a question is marked unanswerable
- **THEN** it is excluded from the hit and rank metrics and its returned evidence count is reported separately

#### Scenario: Retrieval request fails for a question
- **WHEN** the retrieval endpoint returns an error for a question
- **THEN** the question is recorded as failed with its status, counts as not found in every metric, and the run reports how many requests failed

#### Scenario: Retrieval succeeds with a failed channel
- **WHEN** the retrieval endpoint returns HTTP 200 but its metadata reports a failed channel for a question
- **THEN** the question is recorded as a channel failure and counts as not found in every metric

#### Scenario: Expected document cannot be mapped
- **WHEN** a question's expected document has no raw source with the matching title in the workspace
- **THEN** the question is recorded as a mapping failure and counts as not found instead of being scored against a partial expected set

#### Scenario: Failed multi-document question
- **WHEN** a question that expects two documents fails to be measured
- **THEN** it stays in the multi-document question count and counts as found under neither "any" nor "every"

#### Scenario: Duplicate raw source titles
- **WHEN** two raw sources in the workspace share a title
- **THEN** the run refuses to start because the expected documents cannot be resolved unambiguously

### Requirement: Retrieval scoring records are append-only and comparable
The system SHALL write each retrieval scoring run to a new record file containing the run label, source revision, the retrieval policy versions reported by the endpoint, per-question ranked relevance results with their measurement status, and the summary metrics, and MUST refuse to overwrite an existing record file. The system SHALL compare two records over the questions they share and report each metric side by side. A record MUST NOT contain credentials or answer text.

#### Scenario: Output path already exists
- **WHEN** a run is asked to write to a path that already holds a record
- **THEN** the run refuses before calling the retrieval endpoint and the existing file is unchanged

#### Scenario: Two records compared
- **WHEN** two records share 29 answerable questions
- **THEN** the comparison reports every metric for both records over those 29 questions and states the retrieval policy versions of both records

### Requirement: Retrieval scoring records keep per-item channel contributions
Each retrieval scoring record SHALL keep, for every ranked evidence item, the channels that contributed to it and each channel's contribution as returned by the retrieval endpoint, so that a ranking difference between two records can be traced to the channels that produced it. The record MUST NOT add evidence text.

#### Scenario: Contribution kept for a ranked item
- **WHEN** the retrieval endpoint returns an evidence item with contributions from two channels
- **THEN** the record stores both channel names and their contribution values for that item's rank

#### Scenario: Older record without contributions
- **WHEN** a record written before this rule is compared with a newer one
- **THEN** the comparison still reports every metric and does not fail because contributions are missing

### Requirement: Refusal performance reported apart from answerable pass
The run summary, each new scorecard line, and the scorecard page SHALL report three figures separately: answerable questions passed out of answerable questions asked, correct refusals out of unanswerable questions asked, and false refusals out of answerable questions asked. A correct refusal MUST follow the existing unanswerable pass rule. A false refusal MUST be an answerable question whose turn ended in the no-evidence outcome or completed normally with an answer whose first body line begins with the standard refusal statement. The existing pass rate MUST keep its meaning over all questions. The page MUST show the number of unanswerable questions next to the correct-refusal figure. When a run asked no unanswerable question, the correct-refusal figure MUST be reported as absent rather than zero.

#### Scenario: Run with one unanswerable question
- **WHEN** a run of 29 answerable questions and 1 unanswerable question passes 28 answerable questions and correctly refuses the unanswerable one
- **THEN** the summary reports answerable 28/29, correct refusal 1/1, false refusal 0/29, and the overall pass rate stays 29/30

#### Scenario: Answerable question refused
- **WHEN** an answerable question completes normally with an answer whose first body line is the standard refusal statement
- **THEN** it fails as before and is also counted as a false refusal

#### Scenario: Answerable question ends in no evidence
- **WHEN** an answerable question ends in the no-evidence outcome
- **THEN** it fails as before and is counted as a false refusal

#### Scenario: No unanswerable question asked
- **WHEN** a run was limited to answerable questions only
- **THEN** the correct-refusal figure is reported as absent

#### Scenario: Older result file
- **WHEN** a result file written before this rule is rendered
- **THEN** the page derives the three figures from the row fields it already holds and earlier scorecard lines are not rewritten

### Requirement: Replay results record their fixed inputs
Every new answer replay result SHALL record the ingestion snapshot fingerprint computed with the same definition as the retrieval ablation experiment, the question fixture hash, the retrieval policy version, the requested evidence count, and the answer prompt hash. Every new retrieval scoring record SHALL record the ingestion snapshot fingerprint and the question fixture hash with the same definitions. When any of these cannot be determined, the result MUST record it as unknown instead of omitting the run. These fields MUST be additive and MUST NOT change the meaning of existing result fields.

#### Scenario: Replay on the preserved ingestion
- **WHEN** a replay runs on the same ingestion that the retrieval ablation experiment measured
- **THEN** its ingestion snapshot fingerprint equals the one in the ablation record's fixed inputs

#### Scenario: Retrieval scoring on the same ingestion
- **WHEN** a retrieval scoring run and an answer replay run on the same ingestion
- **THEN** both records carry the same ingestion snapshot fingerprint

#### Scenario: Prompt cannot be read
- **WHEN** the answer prompt hash cannot be determined
- **THEN** the result records it as unknown and the run is still written

### Requirement: Paired evidence research evaluation
평가 도구는 같은 문서·위키·청크·임베딩·모델 설정·프롬프트·검색 정책·질문 fixture에서 OFF/ON 1쌍을 실행하고 조건 해시와 양쪽 revision을 기록해야 MUST 한다. 사용자 비용 절감 요청으로 완료된 첫 쌍만 사용하며 반복 안정성은 미측정으로 표시해야 MUST 한다. 문항과 판정 기준은 ON 결과 확인 전에 고정해야 MUST 한다. 조건 불일치는 유효 비교로 표시하면 안 된다. 기존 30문항 회귀 및 비교형 6개·표현 불일치 6개를 포함해야 MUST 한다.

#### Scenario: Matched pair
- **WHEN** 두 실행의 비교 조건 해시가 모두 일치한다
- **THEN** 질문별 결과와 품질·전체 비용·토큰·총 지연 및 첫 답변 토큰 지연 p50/p95를 비교한다

#### Scenario: Corpus or policy changed
- **WHEN** 문서 또는 정책 등 고정 조건 해시가 다르다
- **THEN** 결과를 조건 불일치로 기록하고 개선 근거로 사용하지 않는다

#### Scenario: Decision implementation changed during resume
- **WHEN** 판단 프롬프트·출력 상한을 포함한 실행 코드가 원본 기록 또는 서버 시작 시점과 다르거나 그 지문이 없다
- **THEN** 재개를 거부하고 해당 기록을 동일 조건의 유효 비교로 표시하지 않는다

### Requirement: Recovery scoring uses missing initial evidence
평가 도구는 실제 초기 문맥에서 기대 문서 전체를 확보하지 못한 전용 문항을 복구 대상 분모로 SHALL 사용한다. 최종 문맥의 전체 기대 문서 확보와 필수 사실·이중 인용을 통과한 답변 복구를 별도로 보고해야 MUST 한다. 장애와 측정 누락을 성공으로 세면 안 된다.

#### Scenario: Missing target recovered
- **WHEN** 초기 문맥에 없던 기대 문서가 최종 문맥에 포함되고 답변 판정도 통과한다
- **THEN** 해당 문항은 근거 복구와 답변 복구에 각각 집계된다

#### Scenario: No eligible initial failures
- **WHEN** 초기 문맥이 모든 전용 문항의 기대 문서를 확보했다
- **THEN** 복구 분모는 0이고 복구율은 미측정이며 복구 효과를 주장하지 않는다

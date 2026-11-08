# ask-replay-scorecard Specification

## Purpose

ask 합성 재생의 결과를 질문별 통과 여부, 지연 백분위, 실행 간 누적 기록, 눈으로 볼 수 있는 성적표로 바꿔, 코드나 모델을 바꿨을 때 어느 질문이 왜 떨어졌는지 사람이 따라갈 수 있게 한다.

## Requirements

### Requirement: Per-question pass verdict
The system SHALL assign every replayed question a pass or fail verdict with a single-line reason when it fails. An answerable question MUST pass only when all of the following hold: the turn completed normally, the answer contains zero fabricated anchors, the expected-fact check is not false, and the answer cites both a wiki page and a raw source at least once. A question whose expected-fact check is undefined MUST NOT fail on that criterion. A question marked unanswerable MUST pass only when it contains zero fabricated anchors and either the turn ended in the no-evidence outcome or the turn completed normally with an answer whose first body line, ignoring heading lines and whitespace differences, begins with the standard refusal statement the answer prompt instructs the model to use. A turn that never reached the model MUST fail with a reason naming its outcome.

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

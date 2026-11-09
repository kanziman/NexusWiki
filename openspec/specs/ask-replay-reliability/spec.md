# ask-replay-reliability Specification

## Purpose

같은 조건으로 여러 번 돌린 Ask 합성 재생을 한 묶음으로 읽어, 숫자가 얼마나 흔들리는지와 실패한 문항이 어느 단계에서 처음 틀어졌는지를 사람이 따라갈 수 있게 한다. 한 번의 재생 결과를 효과나 회귀로 오독하지 않게 하는 것이 목적이다.

## Requirements

### Requirement: Repetition series over identical fixed inputs
The system SHALL group two or more answer replay runs into one repetition series only when every run carries the same ingestion snapshot fingerprint, question fixture hash, answer model, retrieval policy version, requested evidence count, and answer prompt hash. It MUST refuse to form a series when any of these differ and MUST name each differing input. A run that lacks any of these values MUST be refused from the series rather than assumed equal. The source revision of each run SHALL be recorded and shown but MUST NOT by itself block grouping.

#### Scenario: Three runs with identical fixed inputs
- **WHEN** three replay runs share every fixed input and differ only in source revision
- **THEN** they form one series and the report lists each run's revision

#### Scenario: One run from a different ingestion
- **WHEN** one of three runs carries a different ingestion snapshot fingerprint
- **THEN** the series is refused and the report names the ingestion snapshot as the differing input

#### Scenario: Run written before fingerprints were recorded
- **WHEN** a replay result has no ingestion snapshot fingerprint
- **THEN** it is refused from the series and the refusal states that the fingerprint is missing

### Requirement: Per-question stability and run-level spread
For a repetition series the system SHALL report, for every question, how many runs it passed out of how many runs it was asked, and SHALL classify it as stable pass when it passed every run, stable fail when it failed every run, and unstable otherwise. Over answerable questions it SHALL report each run's pass count, the minimum, maximum, and mean pass rate across runs, and a 95% interval for each run's pass rate, and SHALL state next to the figures that runs share one synthetic sample and are not independent questions. A question that was not asked in a run because that run stopped early MUST NOT be counted as a failure in that run and MUST be reported as not run.

#### Scenario: Question that passes in some runs
- **WHEN** a question passes in two of three runs
- **THEN** it is reported as 2/3 and classified as unstable

#### Scenario: Spread across runs
- **WHEN** a series has three runs passing 27, 28, and 28 of 29 answerable questions
- **THEN** the report shows each count, a minimum of 27/29, a maximum of 28/29, the mean, and each run's 95% interval

#### Scenario: Run stopped early
- **WHEN** one run stopped after 20 questions
- **THEN** the remaining 10 questions are reported as not run for that run and are not counted as failures

### Requirement: Execution path labeling and ablation record consumption
Every run in a series SHALL be labeled with its execution path: `http` for a replay through the workspace Ask endpoint, or `harness` for answers produced in-process by the retrieval ablation experiment. The system SHALL accept from a retrieval ablation answer record only the condition whose evidence scope is `both` and whose embedding input is `body`, and MUST refuse any other condition of that record. It MUST refuse an ablation record whose experiment identifier is not the retrieval evidence ablation. When a series contains both paths, the report SHALL show the spread over `http` runs alone and over all runs, each labeled with its path composition.

#### Scenario: Ablation record joins a series
- **WHEN** an ablation answer record whose `both` × `body` condition carries the same fixed inputs as two HTTP runs is added to the series
- **THEN** the series holds three runs, the ablation run is labeled `harness`, and the report shows the HTTP-only spread and the all-runs spread separately

#### Scenario: Diagnostic condition offered
- **WHEN** the `source_only` × `body` condition of an ablation record is offered as a run
- **THEN** it is refused because only the `both` × `body` condition matches the product configuration

#### Scenario: Title-header condition offered
- **WHEN** the `both` × `title_body` condition of an ablation record is offered as a run
- **THEN** it is refused because its embedding input differs from the product

### Requirement: Spending cap for repeated replay
A repeated replay SHALL NOT start without an explicit total spending cap. It MUST stop before starting a question whose run would exceed the cap, MUST record the remaining questions and runs as not run with the cap as the reason, and MUST record actual measured cost per run. It MUST refuse non-loopback API or database targets before making any request.

#### Scenario: No cap given
- **WHEN** a repeated replay is requested without a spending cap
- **THEN** it refuses to start and makes no request

#### Scenario: Cap reached in the second run
- **WHEN** the cap is reached partway through the second of three planned runs
- **THEN** the replay stops, the second run is marked partial, the third run is recorded as not run, and the reason names the cap

### Requirement: First broken stage classification
For every failing question in a run the system SHALL assign exactly one automatic first broken stage, checked in this fixed order: execution failure when the turn ended in an HTTP error, an error outcome, or an unknown outcome, or reported a failed retrieval channel, while the no-evidence and fallback outcomes are not execution failures and proceed to the next checks; retrieval miss when a retrieval record for the same ingestion snapshot shows no relevant evidence for the question in its top 8; composition when the retrieval record shows relevant evidence but the answer failed its verdict. Retrieval evidence MUST come only from a retrieval record whose ingestion snapshot fingerprint matches the run; a retrieval scoring record or the `both` × `body` condition of an ablation retrieval record MAY serve. When no matching retrieval record is supplied, a question that is not an execution failure MUST be classified as retrieval evidence unavailable instead of being guessed. The report SHALL count failures per stage per run and SHALL state that the retrieval stage reflects a separate retrieval call on the same ingestion, not the exact context of that turn.

#### Scenario: Gold document absent from retrieval
- **WHEN** a question failed on its expected fact and the matching retrieval record has no relevant evidence in its top 8 with no channel failure
- **THEN** its automatic stage is retrieval miss

#### Scenario: Gold document retrieved but answer wrong
- **WHEN** a question failed on its expected fact and the matching retrieval record ranks relevant evidence within its top 8
- **THEN** its automatic stage is composition

#### Scenario: Turn ended in an HTTP error
- **WHEN** a question's turn ended in an HTTP error
- **THEN** its automatic stage is execution failure regardless of any retrieval record

#### Scenario: Retrieval record from a different ingestion
- **WHEN** the only retrieval record supplied carries a different ingestion snapshot fingerprint
- **THEN** it is refused and failing questions that are not execution failures are classified as retrieval evidence unavailable

#### Scenario: Unanswerable question answered
- **WHEN** an unanswerable question fails because it was answered instead of refused
- **THEN** its automatic stage is composition, because there is no gold document to retrieve

### Requirement: Human cause labels
The system SHALL read a cause label file kept in the repository in which each entry names a question id, a cause from a fixed set — question ambiguity, grader error, or other —, a non-empty evidence reference, and whether the question is a known failure. A label MUST override the automatic stage in the reported first broken stage, and the report MUST show the automatic stage next to the label. The system MUST refuse a label file with an entry whose question id is not in the question fixture, whose cause is outside the fixed set, or whose evidence reference is empty. The label file MUST NOT contain answer text or credentials.

#### Scenario: Labeled question fails
- **WHEN** q06 fails with automatic stage retrieval miss and the label file marks q06 as question ambiguity with evidence #232
- **THEN** the reported first broken stage is question ambiguity and the automatic stage retrieval miss is shown beside it

#### Scenario: Label without evidence
- **WHEN** a label entry has an empty evidence reference
- **THEN** the label file is refused and no report is produced

#### Scenario: Label for an unknown question
- **WHEN** a label entry names a question id that is not in the fixture
- **THEN** the label file is refused and the unknown id is named

### Requirement: Known failures stay in the denominator
A question marked as a known failure SHALL remain in every pass-rate denominator. The report SHALL count, per run and over the series, known failures and unexpected failures separately, where an unexpected failure is any failing question not marked as a known failure. When a known-failure question passes, the report MUST list it as a known failure that passed so the label can be revisited.

#### Scenario: Only the known failure fails
- **WHEN** a run fails only q06 and q06 is a known failure
- **THEN** the pass rate counts q06 as failed, the run shows one known failure and zero unexpected failures

#### Scenario: Known failure passes
- **WHEN** q06 passes in one run of the series
- **THEN** the report lists q06 as a known failure that passed in that run

### Requirement: Reliability report record and offline generation
The system SHALL write each series report to a new record file and MUST refuse to overwrite an existing path. The record SHALL hold the fixed inputs, each run's label, execution path, revision, measured cost, and stop status, the per-question stability and stage results, and the stated limitations. It MUST NOT contain question text, answer text, evidence text, credentials, or workspace identifiers. Producing a report from existing replay results, retrieval records, and the label file MUST NOT contact the API, the database, or any model provider.

#### Scenario: Output path exists
- **WHEN** a report is asked to write to a path that already holds a record
- **THEN** it refuses before reading any input and the existing file is unchanged

#### Scenario: Offline report
- **WHEN** a report is generated with no replay stack running and no network
- **THEN** it succeeds from the given files and incurs no provider cost

## ADDED Requirements

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

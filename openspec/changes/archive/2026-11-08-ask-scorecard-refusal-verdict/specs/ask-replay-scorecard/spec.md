## MODIFIED Requirements

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


## MODIFIED Requirements

### Requirement: Per-turn verdicts and failure signals
For every turn the experiment SHALL record the question type when the question set defines one, status, expected-fact inclusion, whether a forbidden fact was stated, fabricated anchor count, cited source and wiki counts, whether a repair call was made, whether the answer ended as a fallback, whether any answer-model call reached the output token limit, tokens, cost, and latency. A turn MUST count as fact-correct only when its expected fact is included and none of its forbidden facts is stated; a question set without forbidden facts keeps the previous fact-inclusion result. `source_onlyxbody` results MUST be labeled diagnostic and MUST NOT be judged on dual citation. A turn ended by a channel failure, provider error, or missing usage MUST be classified as an execution failure and excluded from fact-inclusion denominators while still being counted and shown. Refusal questions MUST be reported separately from answerable questions.

#### Scenario: Answer ends as a fallback
- **WHEN** a cheap model's answer violates the citation contract, the repair also fails, and the turn ends as a fallback
- **THEN** the turn records repair attempted, fallback true, and its expected-fact inclusion is judged on the fallback text

#### Scenario: Source-only answer
- **WHEN** a `source_onlyxbody` answer cites only raw sources and contains the expected fact
- **THEN** it counts as fact-included, is labeled diagnostic, and is not marked as missing a dual citation

#### Scenario: Answer lists the old and the new value
- **WHEN** a `conflict` question's answer states the newer value and also the older forbidden value
- **THEN** the turn records the forbidden fact as stated and does not count as fact-correct

#### Scenario: Existing sample without types or forbidden facts
- **WHEN** a turn comes from the existing 30-question sample
- **THEN** its type is recorded as absent and its fact-correct result equals its expected-fact inclusion

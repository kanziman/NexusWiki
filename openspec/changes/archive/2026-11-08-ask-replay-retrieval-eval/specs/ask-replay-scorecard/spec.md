## ADDED Requirements

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

# wiki-advantage-evaluation Specification

## Purpose

위키가 이론상 원문보다 유리해야 하는 문항(여러 문서 종합 · 옛/새 규정 충돌 · 길고 지저분한 원문 · 헷갈리는 비슷한 문서)으로 시험지를 따로 만들고, 결과보다 먼저 등록한 기준으로 위키의 정답성 기여를 판정한다.

## Requirements

### Requirement: Typed wiki-advantage question set
The question set SHALL be a separate versioned fixture from the existing replay sample and MUST tag every question with exactly one type among `multi_doc`, `conflict`, `long_noisy`, `distractor`, and `refusal`. It MUST contain at least eight questions of each answerable type and at least three `refusal` questions. A `multi_doc` question's expected fact MUST NOT be stated in any single one of the source documents the question names as its evidence; an expected fact that coincidentally appears in a document the question does not name MUST be reported as a warning, not a failure. A `conflict` question MUST be backed by an older and a newer document that state different values with explicit effective dates, its expected fact MUST be the newer value, and its forbidden facts MUST include the older value. A `long_noisy` question MUST be answered by a source document of at least 4,000 characters. A `distractor` question MUST have at least two other source documents with near-identical titles and structure that state a different value for the same field. The fixture MUST be fixed by content hash before the first paid call of an experiment.

#### Scenario: Multi-document fact stated in one document
- **WHEN** a `multi_doc` question's expected fact appears verbatim in a single one of the documents the question names as evidence
- **THEN** the fixture check fails naming that question and document

#### Scenario: Multi-document fact coincides in an unrelated document
- **WHEN** a `multi_doc` question's expected fact appears in a document the question does not name as evidence
- **THEN** the fixture check passes and reports a warning naming that question and document

#### Scenario: Conflict question without the old value forbidden
- **WHEN** a `conflict` question has no forbidden fact matching the older document's value
- **THEN** the fixture check fails naming that question

#### Scenario: Question without a type
- **WHEN** a question has no type or a type outside the five allowed types
- **THEN** the fixture check fails and no ingestion is started

### Requirement: Fixed cheap compile model
The ingestion for this experiment SHALL compile the wiki with one registered compile model that is different from every registered answer model, and MUST record the compile model, the fixture hash, the ingested document count, the compiled wiki page count, any failed ingestion job, and any job that failed and was recovered through the product's retry path. A job is failed when its final state is a failure state (`dead` or `canceled`); a job that is not yet in a final state, including one waiting for the worker's automatic retry, is unfinished and MUST also block replay. The experiment MUST NOT start answer replay when any ingestion job failed, when any job is unfinished, or when zero wiki pages were compiled. Recovered jobs MUST NOT block replay but MUST be listed in the ingestion record.

#### Scenario: Compile model equals an answer model
- **WHEN** the registered compile model is also one of the registered answer models
- **THEN** registration is refused naming the duplicated model

#### Scenario: One compile job failed
- **WHEN** one document's compile job ends in failure during ingestion
- **THEN** the ingestion record lists the failed job and answer replay for this experiment is refused

#### Scenario: Job recovered by the product retry
- **WHEN** an embedding job died on a provider rate limit and succeeded after the product's retry path
- **THEN** the ingestion record lists it as recovered with its accepted retry count and answer replay is allowed

#### Scenario: Job recovered by the worker's automatic retry
- **WHEN** a job failed once, waited in the automatic-retry state, and succeeded on a later worker attempt
- **THEN** the ingestion record lists it as recovered with its attempt count, and while it was still waiting it counted as unfinished rather than failed

#### Scenario: Job still running when the record is written
- **WHEN** a job is queued or running at the time the ingestion record is written
- **THEN** the ingestion record is not ok and answer replay is refused

### Requirement: Total budget across all phases
The experiment SHALL enforce one total spending cap that covers ingestion, wiki compilation, embeddings, probes, and answer replay. Before ingestion it MUST record the cap. Before registering the replay, it MUST measure the ingestion spend from the replay database and set the replay cap to the total cap minus everything already spent in the experiment workspace. If the remainder cannot fit the registered minimum rounds, no replay is planned and the reason is recorded.

#### Scenario: Ingestion spent part of the budget
- **WHEN** ingestion and compilation spent 80,000 micros under a 1,000,000 micros total cap
- **THEN** the replay registration records a cap of at most 920,000 micros

#### Scenario: Remaining budget too small
- **WHEN** the remaining budget after ingestion cannot cover the registered minimum rounds at the probe cost
- **THEN** no replay runs and the plan records the budget as the reason

### Requirement: Pre-registered effect criterion and verdict
Before the first paid answer call, the experiment SHALL register an effect criterion stating, per answer model, the minimum value of "questions always recovered by the wiki condition minus questions always regressed" over complete rounds, and how many answer models must meet it for the overall verdict to be "supported". After the runs, the experiment MUST report for each model and overall exactly one of `supported`, `not_supported`, or `inconclusive`, where a model's verdict is `inconclusive` when it has fewer than two complete rounds or a measurement failure of its own, and the overall verdict is `inconclusive` when any model has a measurement failure or when no other verdict follows from the registered model count. The verdict MUST be computed only from the registered criterion and MUST NOT be changed after the results are seen.

#### Scenario: Wiki recovers enough questions
- **WHEN** the registered minimum is 3, a model's complete rounds show 4 always-recovered and 0 always-regressed questions, and the registered model count is met
- **THEN** that model's verdict is `supported` and the overall verdict is `supported`

#### Scenario: Wiki shows no difference
- **WHEN** every model shows 0 always-recovered questions over three complete rounds
- **THEN** every model's verdict and the overall verdict are `not_supported`

#### Scenario: Too few complete rounds
- **WHEN** a model has only one complete round because the budget stopped the experiment
- **THEN** that model's verdict is `inconclusive`

### Requirement: Per-type wiki difference report
The scoreboard SHALL show, for each answer model over complete rounds, the fact-correct counts of both conditions, the wiki difference, and the always-recovered and always-regressed questions broken down by question type, alongside the overall effect verdict. `refusal` questions MUST be shown apart from the four answerable types and MUST NOT count toward the effect criterion.

#### Scenario: Wiki helps only on conflicts
- **WHEN** a model's always-recovered questions are all of type `conflict`
- **THEN** the per-type report shows the recovery under `conflict` and zero under the other answerable types

#### Scenario: Refusal question differs between conditions
- **WHEN** a `refusal` question passes under one condition and fails under the other
- **THEN** it is shown in the refusal section and is not counted as recovered or regressed

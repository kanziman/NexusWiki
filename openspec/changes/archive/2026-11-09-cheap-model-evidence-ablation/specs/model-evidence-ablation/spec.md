## Purpose

같은 수집 결과 위에서 답변 모델과 근거 범위(원문만 · 둘 다)를 교차해 반복 재생하고, 위키 근거가 모델별 정답성에 더하는 기여를 사전 등록된 비용 상한 안에서 측정해 JSONL 성적표와 로컬 성적표 화면으로 남긴다.

## ADDED Requirements

### Requirement: Fixed ingestion with only the answer model varying
The experiment SHALL replay answers for every registered answer model under exactly the evidence conditions `source_onlyxbody` and `bothxbody`, reusing one prior retrieval experiment's fixed inputs: ingestion snapshot, question fixture, chunk boundaries, query vectors, embedding version, retrieval policy, graph setting, requested k, and context budget. It MUST NOT re-ingest sources or recompile wiki pages. Before any paid call for a run, it MUST verify that the current ingestion snapshot hash and query-vector hash equal the reused fixed inputs, and MUST refuse the run naming the differing input otherwise. Every run record MUST carry the fixed-input hashes and the answer prompt hash, and runs whose hashes differ MUST NOT be aggregated together.

#### Scenario: Snapshot matches the reused retrieval record
- **WHEN** a run starts on the replay stack whose ingestion snapshot hash equals the reused fixed inputs
- **THEN** the run proceeds and its record carries the same fixed-input hashes as every other run of the experiment

#### Scenario: Stack was re-ingested
- **WHEN** the replay stack's ingestion snapshot hash differs from the reused fixed inputs
- **THEN** the run makes no paid call and stops naming the snapshot as the differing input

### Requirement: Served model must match the registered model
Each run SHALL target exactly one registered answer model. The run MUST confirm, from the recorded usage of every answered turn, that the model actually served equals the run's registered model. A turn whose served model differs, or whose usage is missing, MUST be classified as a measurement failure, not as a correct or incorrect answer, and the run MUST stop at the first such turn.

#### Scenario: Worker serves another model
- **WHEN** a run registered for `openai/gpt-6-luna` receives a turn whose recorded usage names a different model
- **THEN** that turn is a measurement failure, the run stops, and the turn is not counted in any pass or fact-inclusion figure

### Requirement: Pre-registration before any paid call
Before the first paid call of the experiment, the experiment SHALL write a registration that fixes the answer models, the evidence conditions, the maximum and minimum number of rounds, the total spending cap in micros, the probe question, the probe exclusion rule, and the round-reduction rule. The registration MUST be tamper-evident by a content hash. Any probe or run record created at or before the registration time, or under a registration whose content hash no longer matches, MUST be refused. The total spending cap covers probes and runs together.

#### Scenario: Registration edited after creation
- **WHEN** a run is started with a registration whose stored hash no longer matches its content
- **THEN** the run is refused before any paid call

#### Scenario: Run without a cap
- **WHEN** a registration has no positive total spending cap
- **THEN** no probe or run is made

### Requirement: Probe decides executability and round count by cost only
For each registered model, the experiment SHALL run the registered probe question once under `bothxbody` and record its status, served model, tokens, cost, and whether output reached the token limit. A model whose probe is not answered successfully (execution failure, provider refusal, or served-model mismatch) MUST be excluded from all runs and listed as excluded with its reason. The planned round count MUST be the largest value between the registered minimum and maximum such that the spent cost plus the projected cost of all remaining runs stays within the cap, where the projection uses the registered safety factor over the highest observed probe cost per turn. The planning step MUST NOT read any fact-inclusion, pass, or answer-correctness result. If even the registered minimum does not fit, no run is planned and the reason is recorded.

#### Scenario: Probe costs fit three rounds
- **WHEN** all three probes succeed and the projected cost of three rounds plus probe spending is within the cap
- **THEN** the plan records three rounds for all three models

#### Scenario: Probe is refused by the provider
- **WHEN** a model's probe ends in an execution failure
- **THEN** that model is excluded with the failure reason, and the round count is planned over the remaining models

#### Scenario: Probe answer is truncated
- **WHEN** a model's probe answer reaches the output token limit but resolves
- **THEN** the model stays in the plan and the probe record marks the truncation

### Requirement: Round-major execution under the total cap
Runs SHALL execute in round-major order: every planned model and condition of round N completes before any run of round N+1 starts. Before each turn the experiment MUST check that the experiment's total recorded spend plus the next-turn estimate stays within the cap, and MUST stop otherwise, marking the remaining turns and runs as not run with the cap as the reason. Comparisons across models MUST use only rounds that completed for every planned model and condition; a partially completed round MUST be shown as partial and excluded from cross-model figures.

#### Scenario: Cap reached in round three
- **WHEN** the next turn in round three would exceed the total cap
- **THEN** the experiment stops, records the remaining turns as not run, and cross-model comparisons use rounds one and two only

#### Scenario: A round is started out of order
- **WHEN** a run for round two is requested while a planned run of round one has no record
- **THEN** the run is refused naming the missing round-one run

### Requirement: Per-turn verdicts and failure signals
For every turn the experiment SHALL record status, expected-fact inclusion, fabricated anchor count, cited source and wiki counts, whether a repair call was made, whether the answer ended as a fallback, whether any answer-model call reached the output token limit, tokens, cost, and latency. `source_onlyxbody` results MUST be labeled diagnostic and MUST NOT be judged on dual citation. A turn ended by a channel failure, provider error, or missing usage MUST be classified as an execution failure and excluded from fact-inclusion denominators while still being counted and shown. The refusal question MUST be reported separately from answerable questions.

#### Scenario: Answer ends as a fallback
- **WHEN** a cheap model's answer violates the citation contract, the repair also fails, and the turn ends as a fallback
- **THEN** the turn records repair attempted, fallback true, and its expected-fact inclusion is judged on the fallback text

#### Scenario: Source-only answer
- **WHEN** a `source_onlyxbody` answer cites only raw sources and contains the expected fact
- **THEN** it counts as fact-included, is labeled diagnostic, and is not marked as missing a dual citation

### Requirement: Append-only JSONL scoreboard
Each completed or stopped run SHALL append exactly one line to the experiment's JSONL scoreboard and MUST NOT rewrite or delete earlier lines. A line MUST contain the experiment id, round, model, condition, diagnostic flag, planned and asked counts, execution failures, fact-inclusion count over answerable questions, product dual-citation pass count for `bothxbody` only, refusal result, fabricated anchors, repairs, fallbacks, truncations, prompt and completion tokens, total cost, cost per question, latency p50 and p95, git revision, fixed-input hash, and the run record path. Lines MUST NOT contain question text, answer text, credentials, or tokens. Reference lines imported from the prior Sonnet records MUST be marked as reference and MUST NOT be counted as rounds of this experiment.

#### Scenario: Run completes
- **WHEN** a run finishes all 30 questions
- **THEN** one new line with the run's figures is appended and all earlier lines are unchanged

#### Scenario: Broken line in the scoreboard
- **WHEN** the scoreboard file contains a line that is not valid JSON
- **THEN** the scoreboard view skips it and shows how many lines were skipped

### Requirement: Local scoreboard view
The experiment SHALL provide a scoreboard view that reads the JSONL scoreboard on each request and shows one row per run with a fact-inclusion bar, execution failures, fabricated anchors, repairs, fallbacks, truncations, tokens, cost per question, and latency, plus a per-model summary over complete rounds: fact inclusion for each condition, the wiki difference (`bothxbody` minus `source_onlyxbody`), per-question stability counts, and the questions that the wiki condition always recovered or always regressed. It MUST bind only to a loopback address and refuse non-loopback binds, MUST escape every value taken from records, and MUST label diagnostic and reference rows. The same view MUST be exportable as a static HTML file without a network.

#### Scenario: Non-loopback bind requested
- **WHEN** the scoreboard view is asked to listen on a non-loopback address
- **THEN** it stops before listening

#### Scenario: Wiki always recovers a question
- **WHEN** a question misses the expected fact under `source_onlyxbody` and includes it under `bothxbody` in every complete round for a model
- **THEN** the per-model summary lists that question as always recovered by the wiki condition

### Requirement: Product defaults stay unchanged
The experiment SHALL NOT change the product's answer model, embedding input, retrieval policy, Ask dual-citation contract, quality mode, or scorecard verdicts, and MUST run only against the local replay stack, refusing non-loopback targets. Selecting the answer model for a replay worker MUST NOT alter the repository's environment file.

#### Scenario: Experiment completes with a cheap model outperforming
- **WHEN** a cheap model shows a higher wiki gain than the Sonnet reference
- **THEN** the product's configured answer model is unchanged and adopting any model requires a separate change

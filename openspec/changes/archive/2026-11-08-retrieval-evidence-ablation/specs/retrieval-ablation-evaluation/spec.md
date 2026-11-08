## Purpose

같은 수집 결과 위에서 검색 근거(원문만 · 위키만 · 둘 다)와 임베딩 입력(본문만 · 실제 제목+본문)을 교차한 6조건을 비교해, 위키의 기여와 제목 머리말 임베딩의 효과를 분리 측정하고 재사용 가능한 실험 기록으로 남긴다.

## ADDED Requirements

### Requirement: Six-condition matrix over a fixed ingestion
The system SHALL evaluate exactly six conditions formed by crossing the evidence scopes `source_only`, `wiki_only`, and `both` with the embedding inputs `body` and `title_body`. Every condition in one experiment MUST share the same ingestion snapshot, question fixture, chunk boundaries, query vectors, embedding model and provider, retrieval policy version, graph setting, requested k, answer prompt version, and context budget. The experiment MUST record a hash of each fixed input and MUST refuse to compare or aggregate condition results whose fixed-input hashes differ.

#### Scenario: All six conditions share fixed inputs
- **WHEN** an experiment evaluates all six conditions from one ingestion snapshot
- **THEN** every condition record carries the same fixed-input hashes and the results can be compared side by side

#### Scenario: A condition was produced from different inputs
- **WHEN** one condition record has a chunk-boundary, query-vector, or policy hash different from the others
- **THEN** the comparison is refused and the differing input is named instead of a merged result

### Requirement: Title header applies only to the embedding input
For the `title_body` input, the system SHALL embed the text `문서: <title>` followed by a newline and the unchanged chunk body, where the title is the actual raw source title for source chunks and the actual wiki page title for wiki chunks. The title MUST NOT be derived from the question fixture or its expected answers. The stored chunk body, citation coordinates, lexical index, and answer context MUST remain identical to the `body` input. The first experiment MUST NOT add section headings; a section header is a separately versioned input that may be added only when the actual section is deterministically available from the source.

#### Scenario: Source chunk with a real title
- **WHEN** a source chunk from a raw source titled "배송 정책" is embedded with the `title_body` input
- **THEN** the embedded text is `문서: 배송 정책` followed by a newline and the original chunk body, and the chunk's stored content and citation coordinates are unchanged

#### Scenario: Section is not available
- **WHEN** a chunk has no deterministically known section
- **THEN** no section text is added or inferred, and the input remains the title-only version

### Requirement: Distinguishable experiment vectors
Every experiment vector SHALL be identified by its embedding model version, an input-format version, and a hash of the exact embedded text. A vector MUST NOT be reused when any of these differ, including when only the title changed while the body stayed the same. Experiment vectors MUST be stored apart from product embeddings and MUST NOT be read by any product retrieval or Ask request.

#### Scenario: Title changes while body stays the same
- **WHEN** a raw source title changes after a `title_body` vector was created for an unchanged chunk body
- **THEN** the existing vector is not reused and a new vector is required for the new embedded-text hash

#### Scenario: Product request runs during an experiment
- **WHEN** a normal Ask or retrieval request is served while experiment vectors exist
- **THEN** the request uses only product embeddings and its results are unaffected by the experiment

### Requirement: Evidence scope restricts retrieval channels
The `source_only` scope SHALL use only source retrieval channels, the `wiki_only` scope SHALL use only wiki retrieval channels, and the `both` scope SHALL use all first-wave channels. The graph setting MUST be identical across all conditions. Each condition record MUST list which channels were active by design, which succeeded, and which failed.

#### Scenario: Wiki-only scope
- **WHEN** a question is evaluated under `wiki_only`
- **THEN** the ranked evidence contains only wiki pages and the record marks the source channels as disabled by design, not as failed

#### Scenario: A channel fails during a condition
- **WHEN** a vector channel fails under the `both` scope
- **THEN** the record marks that channel as failed and the affected question is classified as an execution failure, not as a retrieval miss

### Requirement: Retrieval-first measurement with pre-registered answer replay
The system SHALL measure retrieval for all six conditions before any answer generation, without calling the answer model. Answer replay MUST run only for conditions chosen by a selection rule and a spending cap recorded before the retrieval results are produced, and MUST stop before exceeding that cap. The experiment MUST NOT make any paid call without an explicit cap.

#### Scenario: Retrieval phase completes
- **WHEN** retrieval has been measured for all six conditions
- **THEN** no answer-model call has been made and the per-condition retrieval results are recorded

#### Scenario: Selection rule recorded after results
- **WHEN** an answer replay is requested with a selection rule recorded after the retrieval results
- **THEN** the replay is refused

#### Scenario: Spending cap reached
- **WHEN** the next answer replay would exceed the recorded spending cap
- **THEN** the replay stops, records the remaining questions as not run, and reports the cap as the reason

### Requirement: Diagnostic verdicts per condition
For every question and condition, the system SHALL record gold-document recall in the ranked evidence and, when answers were replayed, expected-fact inclusion. It MUST classify a non-passing question as a retrieval miss, an execution failure, or an intended single-evidence outcome; in the answer phase, a question whose answer misses the expected fact without any channel failure MUST be classified as an answer failure distinct from a retrieval miss, so that a question answered wrongly despite retrieving its gold document is not attributed to retrieval. Results of `source_only` and `wiki_only` MUST be labeled diagnostic, MUST NOT be judged on dual citation, and MUST NOT be reported as or compared with the product scorecard's dual-citation pass rate. Only `both` conditions MAY additionally carry the product dual-citation verdict.

#### Scenario: Source-only answer without wiki citation
- **WHEN** a `source_only` answer cites only raw sources and contains the expected fact
- **THEN** the question counts as fact-included, is labeled diagnostic, and is not marked as missing a dual citation

#### Scenario: Gold document absent from evidence
- **WHEN** no evidence of the gold document appears in a condition's ranked evidence and all active channels succeeded
- **THEN** the question is classified as a retrieval miss for that condition

#### Scenario: Diagnostic result next to product scorecard
- **WHEN** a summary shows a `wiki_only` condition alongside product results
- **THEN** the `wiki_only` figure is labeled diagnostic and is not presented as a dual-citation pass rate

### Requirement: Append-only reusable experiment record
The system SHALL write each experiment result to a new append-only record and MUST NOT overwrite an existing record. A record MUST include the condition matrix, fixed-input hashes, model and provider, retrieval policy version, k, prompt version, per-question results, per-question failure and recovery between conditions, measured cost, and stated limitations. The record MUST be marked as separate from the rerank OFF/ON experiment and MUST NOT be aggregated with it. It SHALL expose a defined set of publishable fields that the eval publication work can read without the rest of the record.

#### Scenario: Output path already exists
- **WHEN** an experiment is asked to write to an existing record path
- **THEN** it stops without writing and names the existing path

#### Scenario: Question recovers under another condition
- **WHEN** a question misses under `body` and hits under `title_body` for the same evidence scope
- **THEN** the record lists that question as recovered for that comparison

#### Scenario: Publication reads the record
- **WHEN** the eval publication work reads an experiment record
- **THEN** it can obtain only the publishable fields and the record is identified as a different experiment from the rerank comparison

### Requirement: Product defaults stay unchanged
The experiment SHALL NOT change the product's default embedding input, retrieval policy, Ask dual-citation contract, or scorecard verdicts. It MUST run only against a local stack and MUST refuse non-loopback targets.

#### Scenario: Experiment completes
- **WHEN** an experiment finishes with `title_body` outperforming `body`
- **THEN** product ingestion still embeds the body only, and adopting the title header requires a separate change

#### Scenario: Non-loopback target
- **WHEN** the experiment is pointed at a non-loopback database or API address
- **THEN** it stops before making any request

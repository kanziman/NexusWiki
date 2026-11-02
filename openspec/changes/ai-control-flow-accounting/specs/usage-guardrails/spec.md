## MODIFIED Requirements

### Requirement: Usage event accounting
The system SHALL record provider usage for every billable generation and embedding provider call with the workspace, operation category, timestamp, normalized cost, and originating `trace_id` needed for budget aggregation. Compile, conflict judgement, Ask streaming, source and wiki embedding, and query embedding calls MUST all be recorded. A failed validation attempt MUST be recorded separately from the following attempt, and a recording MUST NOT contain prompt or response text.

#### Scenario: Provider reports successful billable usage
- **WHEN** a generation or embedding request completes with provider usage information
- **THEN** the system records one workspace-scoped usage event included in subsequent budget checks

#### Scenario: Structured output is retried after a validation failure
- **WHEN** a provider response fails validation and a later attempt succeeds
- **THEN** the system records one usage event per provider call and the budget total equals the sum of all reported costs

#### Scenario: Every structured attempt fails
- **WHEN** all attempts fail validation and the job ends in failure
- **THEN** the cost of each attempt remains recorded and is included in subsequent budget checks

#### Scenario: Conflict judgement calls the provider
- **WHEN** a conflict check judges a candidate page pair
- **THEN** the system records that call's usage against the same workspace and job before applying the judgement

#### Scenario: Ask stream is aborted
- **WHEN** a client disconnects or the stream ends before final provider usage arrives
- **THEN** the system still records one usage event for the call and marks it as incomplete, using any usage already reported

#### Scenario: Query embedding completes
- **WHEN** a query is embedded for retrieval
- **THEN** the system records an embedding usage event with the request's `trace_id`, and a recording failure is logged without failing the query

#### Scenario: Job is retried after usage was recorded
- **WHEN** an at-least-once retry repeats a provider call
- **THEN** each actual provider call is counted and an earlier call's event is not overwritten

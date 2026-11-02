# usage-guardrails Specification

## Purpose

워크스페이스별 LLM·임베딩 비용과 장시간 파이프라인을 제한하고 관측하되, 운영 화면이나 오류를 통해 공급자 비밀정보가 노출되지 않도록 한다.

## Requirements

### Requirement: Workspace budget preflight
The system MUST compare the complete current billing-window usage with the workspace budget before accepting new billable work and MUST reject work when spending has reached or exceeded the cap.

#### Scenario: Workspace has reached its monthly cap
- **WHEN** a member submits billable work and complete monthly usage is equal to the workspace cap
- **THEN** the system rejects the work with a distinguishable budget-limit outcome and creates no billable successor job

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

#### Scenario: A billed response is rejected
- **WHEN** a provider response is unusable because its content is missing, its host differs from the requested provider, or its vector dimensions are wrong
- **THEN** the system records the reported usage before raising the failure, and the cost is included in subsequent budget checks

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

### Requirement: Safe operations snapshot
The system SHALL provide owners and editors with a bounded operations snapshot containing budget totals and aggregate pipeline health, and MUST NOT include job payloads, raw errors, provider credentials, or model secrets.

#### Scenario: Editor opens workspace operations
- **WHEN** a workspace editor requests the operations snapshot
- **THEN** the system returns the allowlisted budget and stage aggregates without sensitive operational internals

#### Scenario: Viewer requests workspace operations
- **WHEN** a workspace viewer or non-member requests the operations snapshot
- **THEN** the system denies access without returning operational aggregates

### Requirement: Input size guardrail
The system MUST reject source input that exceeds the configured size or length limit before scheduling billable processing.

#### Scenario: Source exceeds the accepted limit
- **WHEN** a member submits a file, URL, or text payload beyond its configured limit
- **THEN** the system rejects the request before creating downstream billable jobs

### Requirement: User-facing free credit quota feedback and limit modal
The system SHALL present an actionable free credit quota limit dialog (`CreditLimitModal`) whenever a member encounters a budget limit rejection (`402 budget_exceeded`) during conversational asking or source ingestion. The dialog SHALL inform the user that their monthly free credit quota has been exhausted, state that the quota resets on the 1st of the next month, and provide direct access to view usage details in settings.

#### Scenario: Member asks question with exhausted monthly budget
- **WHEN** a member submits a question in `AskConversation` or `AskHero` and receives a 402 budget_exceeded response
- **THEN** the system halts streaming and displays the credit limit dialog explaining the monthly free credit quota exhaustion

#### Scenario: Member uploads source with exhausted monthly budget
- **WHEN** a member uploads a file, URL, or text in `Dropzone` and receives a 402 budget_exceeded response
- **THEN** the system halts the upload pipeline and presents the credit limit dialog


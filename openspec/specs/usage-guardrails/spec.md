# usage-guardrails Specification

## Purpose

워크스페이스별 LLM·임베딩 비용과 장시간 파이프라인을 제한하고 관측하되, 운영 화면이나 오류를 통해 공급자 비밀정보가 노출되지 않도록 한다.

## Requirements

### Requirement: Workspace budget preflight
The system MUST compare the complete current billing-window usage with the workspace budget before accepting new billable work and MUST reject work when spending has reached or exceeded the cap. For Ask calls, the budget decision MUST also include durable temporary reservations for in-flight and unresolved calls without double-counting any recorded cost for the same call. A new Ask provider call MUST NOT start unless its temporary reservation can be atomically admitted within the remaining budget.

#### Scenario: Workspace has reached its monthly cap
- **WHEN** a member submits billable work and complete monthly usage is equal to the workspace cap
- **THEN** the system rejects the work with a distinguishable budget-limit outcome and creates no billable successor job

#### Scenario: Repeated interruption consumes the remaining budget
- **WHEN** unresolved interrupted Ask calls have temporarily consumed the remaining budget
- **THEN** a new Ask is rejected with the budget-limit outcome even if the interrupted calls have not yet reported their final costs

#### Scenario: Concurrent Ask admission
- **WHEN** concurrent Ask calls compete for the same remaining workspace budget
- **THEN** their admitted reservations do not together exceed that remaining budget and rejected calls do not contact the provider

#### Scenario: Budget state cannot be persisted
- **WHEN** the temporary reservation cannot be durably recorded
- **THEN** the provider is not called and the failure is not reported as a successful admission

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

### Requirement: 중단 Ask 비용 정산
The system SHALL preserve a server-owned call identity, workspace, trace, originating billing window, temporary reservation, and any available provider generation identifier for each admitted Ask call. It MUST reconcile interrupted calls against provider-reported cost when that cost is available. Previously recorded usage events MUST NOT be overwritten or deleted. Settlement MUST be idempotent, preserve an audit trail, and replace the temporary budget contribution with the confirmed cost without double-counting. Estimates MUST NOT be represented as provider-confirmed cost.

#### Scenario: Provider cost becomes available
- **WHEN** a previously unresolved call obtains a valid final cost from the provider
- **THEN** the confirmed cost is accounted for once, the associated temporary contribution is released atomically with settlement, and earlier usage events remain unchanged

#### Scenario: Reconciliation is retried or performed concurrently
- **WHEN** multiple attempts reconcile the same provider call
- **THEN** the effective cost is accounted for once and no earlier event is overwritten

#### Scenario: Generation ID is missing or lookup fails
- **WHEN** a call has no generation ID or the provider lookup returns an error or no conclusive final cost
- **THEN** the call remains unresolved with its temporary budget contribution retained, and it is not settled as zero solely because lookup failed

#### Scenario: Worker restarts during an interrupted call
- **WHEN** the worker restarts after a provider call was admitted but before its final accounting completed
- **THEN** the durable reservation remains discoverable and contributes to budget decisions until confirmed settlement or confirmed evidence that no billable call occurred

#### Scenario: Month boundary occurs before settlement
- **WHEN** a call is settled after the billing window in which it was admitted
- **THEN** its reservation and confirmed cost are attributed consistently to the originating window, and settlement does not create a duplicate charge in the new window

### Requirement: Conservative reservation policy and tenant boundary
The system MUST define the temporary reservation calculation and its assumptions in code and operational documentation, enforce the request limits used by that calculation, and document any remaining bound or uncertainty in unaccounted cost. It MUST NOT claim a hard billing bound based solely on an unverified estimate. Only trusted worker accounting paths MAY reserve or settle calls; user-supplied workspace or generation identifiers MUST NOT authorize cross-workspace reads or cost changes. Reconciliation MUST NOT persist prompt or answer bodies or expose provider credentials.

#### Scenario: Unsupported reservation assumptions
- **WHEN** the system cannot apply the configured reservation policy to a requested model or request
- **THEN** the Ask provider call is not started and the reason is observable without exposing credentials or content

#### Scenario: A user attempts to settle another workspace's call
- **WHEN** a user submits or reuses another workspace's call or generation identifier
- **THEN** no reservation, cost, or lookup result from that workspace is exposed or changed

### Requirement: 구조화 출력 호출의 입력·출력 토큰 상한
시스템은 컴파일과 충돌 판정을 포함한 모든 구조화 출력 LLM 호출에 설정된 입력 토큰 상한과 출력 `max_tokens` 상한을 MUST 적용해야 한다. 공급자 요청 본문에는 `max_tokens`가 명시적으로 포함되어야 하며, 입력이 상한에서 잘렸는지 여부와 적용된 `max_tokens`는 본문 없이 사용량 메타데이터에 SHALL 기록한다.

#### Scenario: 컴파일과 충돌 판정이 공급자를 호출한다
- **WHEN** 워커가 컴파일 또는 충돌 판정을 위해 구조화 출력 호출을 보낸다
- **THEN** 공급자 요청에 각 작업의 `max_tokens` 상한이 실리고 사용량 메타데이터에 기록된다

#### Scenario: 긴 위키 본문 쌍의 충돌 판정 입력 제한
- **WHEN** 충돌 판정 대상 위키 페이지 본문이 설정된 입력 토큰 상한을 넘는다
- **THEN** 프롬프트 입력은 상한 안에서 잘려 전송되고 잘림 여부가 사용량 메타데이터에 기록된다

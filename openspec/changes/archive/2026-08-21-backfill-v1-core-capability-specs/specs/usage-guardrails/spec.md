## Purpose

워크스페이스별 LLM·임베딩 비용과 장시간 파이프라인을 제한하고 관측하되, 운영 화면이나 오류를 통해 공급자 비밀정보가 노출되지 않도록 한다.

## ADDED Requirements

### Requirement: Workspace budget preflight
The system MUST compare the complete current billing-window usage with the workspace budget before accepting new billable work and MUST reject work when spending has reached or exceeded the cap.

#### Scenario: Workspace has reached its monthly cap
- **WHEN** a member submits billable work and complete monthly usage is equal to the workspace cap
- **THEN** the system rejects the work with a distinguishable budget-limit outcome and creates no billable successor job

### Requirement: Usage event accounting
The system SHALL record provider usage for billable generation and embedding work with the workspace, operation category, timestamp, and normalized cost needed for budget aggregation.

#### Scenario: Provider reports successful billable usage
- **WHEN** a generation or embedding request completes with provider usage information
- **THEN** the system records one workspace-scoped usage event included in subsequent budget checks

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

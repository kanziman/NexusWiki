## Purpose

장시간 수집·컴파일 작업이 at-least-once 실행 환경에서도 관측 가능하고 재시도 가능하며 중복 비용이나 비밀정보 노출 없이 안전하게 종료되도록 한다.

## ADDED Requirements

### Requirement: Observable staged job chain
The system SHALL represent source processing as the ordered core stages `parse`, `compile`, `link_sync`, and `embed`, followed by `conflict_check` when compiled wiki pages require quality evaluation, and SHALL expose each applicable stage's current state rather than only an indeterminate global spinner.

#### Scenario: Source advances through processing
- **WHEN** a source finishes one processing stage and enters the next
- **THEN** the source job view reports the actual completed, active, and remaining stage states

### Requirement: Atomic and idempotent stage transition
Each job stage MUST have an idempotency identity, and completing one stage while scheduling its successor MUST behave atomically so retries cannot create parallel duplicate successors.

#### Scenario: Completion acknowledgement is retried
- **WHEN** a worker repeats a stage completion after an uncertain network result
- **THEN** the system preserves one completed stage and at most one successor for the same idempotency identity

### Requirement: Stale job reclamation
The system SHALL reclaim a running job only after its lease exceeds a timeout derived from observed processing duration, and all handlers MUST tolerate at-least-once execution.

#### Scenario: Worker disappears while holding a job
- **WHEN** a running job stops renewing its lease beyond the configured stale threshold
- **THEN** the system safely makes the job eligible for retry without allowing duplicate durable outputs

### Requirement: User-controlled retry and cancellation
The system SHALL allow authorized members to retry a dead job and request cancellation of cancellable queued or running work.

#### Scenario: Member retries a dead job
- **WHEN** an authorized member retries a dead source-processing job
- **THEN** the system enqueues a new safe attempt and makes the new attempt observable

#### Scenario: Member cancels work
- **WHEN** an authorized member cancels a cancellable job
- **THEN** the system prevents unstarted successor work and reports the cancellation state

### Requirement: Safe job errors
The system MUST sanitize provider failures before storing or exposing job errors and MUST NOT include API keys, credentials, or raw provider response bodies.

#### Scenario: Provider error contains a credential
- **WHEN** an external provider failure includes secret material
- **THEN** the persisted and user-visible job error omits the secret while retaining an actionable failure category

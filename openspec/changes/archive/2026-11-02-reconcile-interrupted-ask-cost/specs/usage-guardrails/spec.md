## MODIFIED Requirements

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

## ADDED Requirements

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

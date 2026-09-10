## MODIFIED Requirements

### Requirement: Failure-specific recovery details
The system SHALL reveal an error summary and recovery action for a failed source-processing stage. The error summary SHALL identify the failed stage and use human-readable failure guidance rather than raw machine tokens for known terminal states. For failures caused by provider credit exhaustion, the system SHALL display human-readable guidance instructing the user to recharge credits or verify workspace API keys, and SHALL provide an accessible retry action so the user can re-run after recharging.

#### Scenario: Failed stage offers recovery
- **WHEN** a source-processing stage is dead from a retryable error
- **THEN** the summary displays that stage's failure detail and an accessible retry action for that job

#### Scenario: Provider credit exhaustion guides recharging and preserves recovery
- **WHEN** a source-processing stage fails due to provider credit exhaustion
- **THEN** the summary displays a human-readable message instructing the user to recharge credits or verify workspace API keys, and provides an accessible retry action

#### Scenario: Non-failed source does not expose failure detail
- **WHEN** no source-processing stage is dead
- **THEN** the summary does not display an error detail or retry action

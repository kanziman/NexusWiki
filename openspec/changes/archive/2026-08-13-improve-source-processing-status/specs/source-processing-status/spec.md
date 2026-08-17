## Purpose

소스 목록에서 처리 작업의 현재 상태와 다음 행동을 짧고 명확하게 전달해 사용자가 처리 상황을 빠르게 파악하게 한다.

## ADDED Requirements

### Requirement: Compact processing summary
The system SHALL render one compact processing summary for every source whose processing job chain is loaded. The summary SHALL expose the current processing state and completed-stage progress without rendering the full stage list by default.

#### Scenario: Processing source displays its current stage and progress
- **WHEN** one or more source-processing jobs are queued or running
- **THEN** the summary displays the first queued or running stage and the number of completed stages out of the five source-processing stages

#### Scenario: Completed source displays completion progress
- **WHEN** all source-processing stages have succeeded
- **THEN** the summary displays completion progress and does not display a retry action or error detail

### Requirement: Failure-specific recovery details
The system SHALL reveal an error summary and retry action only for a failed source-processing stage. The error summary SHALL identify the failed stage and use a bounded version of the recorded error message.

#### Scenario: Failed stage offers recovery
- **WHEN** a source-processing stage is dead
- **THEN** the summary displays that stage's failure detail and an accessible retry action for that job

#### Scenario: Non-failed source does not expose failure detail
- **WHEN** no source-processing stage is dead
- **THEN** the summary does not display an error detail or retry action

### Requirement: Existing processing controls remain available
The system SHALL preserve existing polling, retry, and cancellation behavior while presenting the compact summary. A cancellable queued or running job SHALL retain an accessible cancellation action and confirmation flow.

#### Scenario: Current job can be cancelled
- **WHEN** the current source-processing job is queued or running
- **THEN** the summary provides the existing accessible cancellation action and confirmation dialog

#### Scenario: Retried job resumes status updates
- **WHEN** a user retries a failed job after polling has stopped
- **THEN** the system resumes polling and refreshes the compact summary with the returned job state

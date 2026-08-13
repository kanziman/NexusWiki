# autonomous-workflow Specification

## Purpose

사용자가 명시적으로 연속 진행을 승인한 change를 반복 확인 없이 계획, 검증, 아카이브까지 안전하고 일관되게 완료하도록 한다.

## Requirements

### Requirement: Continuous change completion
The agent SHALL continue an explicitly authorized change through planning, implementation, validation, spec sync, archive, and confirmed external updates without repeated approval.

#### Scenario: Explicit continuous authorization
- **WHEN** a user requests continuous progress without approval
- **THEN** the agent completes each workflow stage until completion or a defined exception

### Requirement: Autonomous workflow exceptions
The agent MUST pause for unavailable external authority or credentials, material ambiguity, or failed required validation.

#### Scenario: Missing external credential
- **WHEN** implementation requires a user-owned external credential
- **THEN** the agent reports the needed authority and continues only independent work

## Why

Sources 목록이 모든 처리 단계를 반복해 보여줘 현재 상태와 필요한 행동을 빠르게 파악하기 어렵다.

## What Changes

- 처리 상태를 현재 단계와 진행률 중심의 compact summary로 표시한다.
- 실패한 작업에만 오류와 재시도 행동을 노출하고, 기존 polling·retry·cancel을 유지한다.

## Capabilities

### New Capabilities

- `source-processing-status`: 소스 처리 상태의 compact·actionable 표시 계약

### Modified Capabilities

- 없음.

## Impact

- dashboard Sources 목록과 JobStepper 상태 표시; API·DB·권한 계약은 변경하지 않는다.

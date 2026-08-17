## Why

반복 확인으로 완료된 change의 적용·검증·아카이브 흐름이 불필요하게 멈춘다.

## What Changes

- 사용자가 연속 진행을 명시하면 계획부터 archive까지 중단 없이 수행하는 규칙을 문서화한다.
- 외부 자격 증명, 권한, material ambiguity, 검증 실패만 중단 예외로 둔다.

## Capabilities

### New Capabilities

- `autonomous-workflow`: repository agent의 연속 실행 계약

### Modified Capabilities

- 없음.

## Impact

- `AGENTS.md` workflow 문서; 제품 런타임 동작은 변경하지 않는다.

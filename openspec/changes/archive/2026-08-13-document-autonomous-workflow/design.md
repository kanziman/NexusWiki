## Context

AGENTS.md는 explicit apply를 요구하지만 연속 진행 권한을 정의하지 않는다.

## Decisions

- 사용자의 연속 진행 요청을 이후 scoped change의 apply 권한으로 해석한다.
- 외부 권한, material ambiguity, 검증 실패에서는 중단한다.

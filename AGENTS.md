# NexusWiki Agent Workflow

## 기본 원칙

- 기존 작업 트리의 무관한 변경은 보존하고, 저장소 편집에는 `apply_patch`를 사용한다.
- 사용자 행동이나 외부 계약을 바꾸는 작업은 하나의 OpenSpec change로 명확히 분리한다.
- `.claude/CLAUDE.md`의 프로젝트 제약과 코드 관례를 항상 함께 따른다.

## 필수 작업 순서

1. 구현 전에 Linear 이슈를 생성하거나 기존 이슈를 확인한다. OpenSpec change를 만들면 이슈 설명에 경로를 연결한다.
2. `openspec-propose`로 필요한 산출물을 만들고 `openspec validate <change> --strict`를 통과시킨다.
3. 사용자가 명시적으로 apply를 요청한 뒤에만 `openspec-apply-change`로 구현한다. 각 검증된 task를 즉시 완료 처리한다.
4. 완료를 주장하기 전에 관련 테스트, typecheck, lint, strict OpenSpec validation을 새로 실행한다. 실패한 검증이 있으면 해당 task를 완료 처리하지 않는다.
5. delta spec이 있는 change는 아카이브 전에 `openspec-sync-specs`로 `openspec/specs/`에 동기화하고 spec 검증을 실행한다.
6. 모든 task와 필요한 산출물이 완료된 뒤에만 `openspec-archive-change`로 아카이브한다.
7. 아카이브가 확인된 뒤 Linear 이슈를 완료 상태로 갱신한다.

## 연속 진행 권한

- 사용자가 “한번에 진행”, “승인없이 계속”, “이어서 진행”처럼 연속 진행을 명시하면, 해당 요청 범위의 후속 change는 Linear 이슈 생성부터 OpenSpec 제안·apply·검증·spec sync·archive까지 반복 승인 없이 진행한다.
- 이 권한은 이미 검증된 task의 완료 처리와 아카이브를 멈추지 않는다. 완료 후에는 다음 미차단 우선순위 이슈로 이동한다.
- 외부 자격 증명·권한, material ambiguity, 필수 검증 실패, 또는 사용자 범위를 벗어나는 변경만 중단하고 필요한 후속 조치를 보고한다.

## 커넥터 제약

- Linear 등 외부 커넥터가 workflow state UUID처럼 필요한 식별자를 제공하지 않으면 값을 추측하지 않는다.
- 외부 상태 변경은 커넥터 응답으로 성공을 확인한 경우에만 완료로 보고한다. 불가능하면 이슈를 그대로 두고 제한과 필요한 후속 조치를 보고한다.

## 문서·도구 작업

- 개발 workflow나 검증 계약을 바꾸는 문서·도구 작업도 OpenSpec change로 관리한다.
- 순수 문서 편집은 사용자와 범위를 확인하고 관련 검증만 실행한다.

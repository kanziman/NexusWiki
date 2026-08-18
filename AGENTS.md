# NexusWiki Agent Workflow

이 문서는 Codex 등 에이전트가 공유하는 저장소 workflow 계약이다. Claude Code는 `.claude/CLAUDE.md`의 「Agent Workflow」절과 `.claude/commands/opsx/*`를 함께 사용한다. 두 진입점은 같은 OpenSpec 계약을 가리키며, 계약 본문은 `openspec/specs/`에 있다.

## 기본 원칙

- 기존 작업 트리의 무관한 변경은 보존하고, 저장소 편집에는 `apply_patch`를 사용한다.
- 사용자 행동이나 외부 계약을 바꾸는 작업은 하나의 OpenSpec change로 명확히 분리한다.
- `.claude/CLAUDE.md`의 프로젝트 제약과 코드 관례를 항상 함께 따른다.
- 작업 추적은 **GitHub Issues + `kanziman` Project #1**만 사용한다. Linear는 사용하지 않는다.
- 커밋 메시지와 **PR 제목·본문은 한국어**로 쓴다. squash merge가 PR 제목을 `main`의 커밋 제목으로 만든다.
- 커밋 메시지와 PR 본문에 `Co-Authored-By:` 트레일러나 도구 서명을 붙이지 않는다.

## 계약 위치

| 계약 | 스펙 |
| --- | --- |
| 계획 게이트 · 수직 슬라이스 · GitHub 이슈 계층 | `openspec/specs/feature-planning-workflow/spec.md` |
| 연속 진행 권한과 중단 예외 | `openspec/specs/autonomous-workflow/spec.md` |
| commit 범위 · PR 발행 안전 규칙 | `openspec/specs/pull-request-workflow/spec.md` |
| 커밋 메시지 형식 · AC 인수 조건 | `docs/reference/commit.md` |

⚠️ 세부 규칙을 이 문서에 복제하지 않는다. 규칙이 바뀌면 스펙을 OpenSpec change로 고친다. 복제본을 만들면 두 곳이 조용히 어긋난다.

## 필수 작업 순서

1. 구현 전에 GitHub umbrella 이슈를 생성하거나 기존 이슈를 확인하고 Project #1에 `Todo`로 추가한다. OpenSpec change를 만들면 이슈 본문에 change 경로를 연결한다.
2. `openspec new change "<name>"`으로 change를 만든다. `openspec status --change "<name>" --json`이 지시하는 다음 산출물을 `openspec instructions "<artifact>" --change "<name>" --json`의 안내대로 작성한다. 산출물 순서는 `proposal` → `specs` → `design` → `tasks`이다.
3. `openspec validate "<name>" --strict`를 통과시킨다.
4. 사용자가 명시적으로 apply를 요청한 뒤에만 `openspec instructions apply --change "<name>" --json`의 안내대로 구현한다. 검증된 task는 즉시 완료 처리한다.
5. 완료를 주장하기 전에 관련 테스트 · typecheck · lint와 strict validation을 **새로** 실행한다. 실패한 검증이 있으면 해당 task를 완료 처리하지 않는다.
6. delta spec이 있는 change는 아카이브 전에 delta를 `openspec/specs/`에 반영하고 `openspec validate --specs --strict`를 실행한다.
7. 모든 task와 필요한 산출물이 완료된 뒤에만 `openspec instructions archive --change "<name>" --json`을 확인하고 `openspec archive "<name>"`을 실행한다.
8. 아카이브가 확인된 뒤 sub-issue를 닫는다. umbrella 이슈는 아카이브 성공 이후에만 닫는다.

## 연속 진행 권한

계약: `openspec/specs/autonomous-workflow/spec.md`

- 사용자가 "한번에 진행", "승인없이 계속", "이어서 진행"처럼 연속 진행을 명시하면, 해당 요청 범위의 change를 이슈 생성부터 제안 · apply · 검증 · spec sync · archive까지 반복 승인 없이 진행한다.
- 이 권한은 이미 검증된 task의 완료 처리와 아카이브를 멈추지 않는다. 완료 후에는 다음 미차단 우선순위 이슈로 이동한다.
- ⚠️ 다음 세 경우에만 중단하고 필요한 후속 조치를 보고한다. 그 외의 사유로 멈추면 권한을 위반한 것이다.
  1. **외부 권한·자격 증명 부재** — 사용자만 가진 credential이 필요할 때. 독립적으로 가능한 작업은 계속한다.
  2. **material ambiguity** — 해석에 따라 결과 계약(사용자 흐름 · 경계 동작 · 용어)이 달라질 때.
  3. **필수 검증 실패** — 실패한 검증이 있으면 해당 task를 완료 처리하지 않는다.

## 외부 상태 제약

- GitHub 명령이 필요한 식별자(이슈 번호, Project item id 등)를 반환하지 않으면 값을 추측하지 않는다.
- 외부 상태 변경은 명령 응답으로 성공을 확인한 경우에만 완료로 보고한다. 확인이 불가능하면 이슈를 그대로 두고 제한과 필요한 후속 조치를 보고한다.

## 문서·도구 작업

- 개발 workflow나 검증 계약을 바꾸는 문서·도구 작업도 OpenSpec change로 관리한다.
- 순수 문서 편집은 사용자와 범위를 확인하고 관련 검증만 실행한다.

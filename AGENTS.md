# NexusWiki Agent Workflow

이 문서는 에이전트가 공유하는 저장소 workflow 계약이다. OpenSpec 계약 본문은 `openspec/specs/`에 있다.

## 기본 원칙

- 기존 작업 트리의 무관한 변경은 보존하고, 저장소 편집에는 `apply_patch`를 사용한다.
- 사용자 행동이나 외부 계약을 바꾸는 작업은 하나의 OpenSpec change로 명확히 분리한다.
- `.claude/CLAUDE.md`의 프로젝트 제약과 코드 관례를 항상 함께 따른다.
- 작업 추적은 **GitHub Issues**만 사용한다. Linear는 사용하지 않는다.
- 커밋 메시지와 **PR 제목·본문은 한국어**로 쓴다. squash merge가 PR 제목을 `main`의 커밋 제목으로 만든다.
- 커밋 메시지와 PR 본문에 `Co-Authored-By:` 트레일러나 도구 서명을 붙이지 않는다.

## 계약 위치

| 계약 | 스펙 |
| --- | --- |
| 계획 게이트 · 수직 슬라이스 · GitHub 이슈 계층 | `openspec/specs/feature-planning-workflow/spec.md` |
| commit 범위 · PR 발행 안전 규칙 | `openspec/specs/pull-request-workflow/spec.md` |
| 커밋 메시지 형식 · AC 인수 조건 | `docs/reference/commit.md` |

⚠️ 세부 규칙을 이 문서에 복제하지 않는다. 규칙이 바뀌면 스펙을 OpenSpec change로 고친다. 복제본을 만들면 두 곳이 조용히 어긋난다.

## 필수 작업 순서

1. 구현 전에 GitHub umbrella 이슈를 생성하거나 기존 이슈를 확인한다. OpenSpec change를 만들면 이슈 본문에 change 경로를 연결한다.
2. `openspec new change "<name>"`으로 change를 만든다. `openspec status --change "<name>" --json`이 지시하는 다음 산출물을 `openspec instructions "<artifact>" --change "<name>" --json`의 안내대로 작성한다. 산출물 순서는 `proposal` → `specs` → `design` → `tasks`이다.
3. `openspec validate "<name>" --strict`를 통과시킨다.
4. 사용자가 명시적으로 apply를 요청한 뒤에만 `openspec instructions apply --change "<name>" --json`의 안내대로 구현한다. 검증된 task는 즉시 완료 처리한다.
5. 완료를 주장하기 전에 관련 테스트 · typecheck · lint와 strict validation을 **새로** 실행한다. 실패한 검증이 있으면 해당 task를 완료 처리하지 않는다.
6. delta spec이 있는 change는 아카이브 전에 delta를 `openspec/specs/`에 반영하고 `openspec validate --specs --strict`를 실행한다.
7. 모든 task와 필요한 산출물이 완료된 뒤에만 `openspec instructions archive --change "<name>" --json`을 확인하고 `openspec archive "<name>"`을 실행한다. ⚠️ 완료 후 **커밋까지만 하고 멈춘다** — push · PR로 바로 진행하지 않는다.
8. 리뷰 게이트 2종(`spec-conformance-reviewer` · `tenant-isolation-reviewer`)을 실행한다. 판정 기준 · 라운드 상한은 `.claude/CLAUDE.md`의 「리뷰 게이트」가 정본이다. `needs_fix`면 지적 사항을 수정하고 4단계부터 다시 검증을 진행한다. `blocked`이면 사람에게 넘긴다.
9. 리뷰가 `pass`로 확정된 뒤에만 `pull-request-workflow` 스펙에 따라 PR을 연다.
10. PR이 열린 뒤 sub-issue를 닫는다. umbrella 이슈는 PR 머지 이후에만 닫는다.

## 외부 상태 제약

- GitHub 명령이 필요한 식별자(이슈 번호 등)를 반환하지 않으면 값을 추측하지 않는다.
- 외부 상태 변경은 명령 응답으로 성공을 확인한 경우에만 완료로 보고한다. 확인이 불가능하면 이슈를 그대로 두고 제한과 필요한 후속 조치를 보고한다.

## 문서·도구 작업

- 개발 workflow나 검증 계약을 바꾸는 문서·도구 작업도 OpenSpec change로 관리한다.
- 순수 문서 편집은 사용자와 범위를 확인하고 관련 검증만 실행한다.

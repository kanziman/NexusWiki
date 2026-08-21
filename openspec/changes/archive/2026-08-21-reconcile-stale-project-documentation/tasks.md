## 1. 활성 문서 원장 정리

- [x] 1.1 `.claude/CLAUDE.md`와 `docs/reference/conventions.md`에서 현재 작업·결정 원장을 GitHub Issues와 OpenSpec으로 정렬하고 존재하지 않는 `HANDOFF.md` 지시를 제거한다.
- [x] 1.2 `checklists.json`과 `checklists_v2.json`에 역사적 GSD 스냅샷 lifecycle metadata를 추가하고 기존 task·decision·verification 기록이 보존되는지 확인한다.
- [x] 1.3 `docs/reference/architecture.md`, `docs/reference/stack.md`, `docs/architecture/index.html`의 checklist·HANDOFF 출처 설명을 현재/역사 문서 구분에 맞게 교정한다.

## 2. 현재 사실 주장 교정

- [x] 2.1 `docs/reference/architecture.md`와 `docs/reference/stack.md`를 migration `0017`, 13개 테이블, 현재 queue 함수와 코드 구조에 맞게 갱신한다.
- [x] 2.2 `docs/design-systems/v2/PRODUCT-INVARIANTS.md`의 slug·공개 공유 구현 상태, 테이블 수, 내부 UUID route 설명을 현재 구현에 맞게 교정한다.
- [x] 2.3 `README.md`의 중복 commit 규칙을 canonical reference 링크로 교체하고 `docs/design-systems/v2/nexuswiki-design-system.md`의 TODO 개수를 본문과 일치시킨다.

## 3. 검증

- [x] 3.1 두 checklist의 UTF-8 JSON 파싱과 변경 문서의 상대 링크·경로 유효성을 검증한다.
- [x] 3.2 migration·테이블·queue 함수·route·TODO 수와 제거 대상 stale 원장 참조를 저장소에서 새로 대조한다.
- [x] 3.3 변경 파일의 잠재적 secret 패턴을 검사하고 `openspec validate reconcile-stale-project-documentation --strict`를 통과시킨다.

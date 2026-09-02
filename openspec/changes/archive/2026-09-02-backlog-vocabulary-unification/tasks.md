## 1. 목적지 명칭 통일

- [x] 1.1 `apps/dashboard/components/BacklogList.tsx`의 `h1`을 `지식 공백`으로 바꾼다.
  - Given: 멤버가 백로그 전용 화면을 연다
  - When: 화면 제목이 렌더링된다
  - Then: 제목이 `지식 공백`이며 홈 섹션이 쓰는 앞머리 명칭과 같다
- [x] 1.2 `apps/dashboard/components/WorkspaceShell.tsx`의 브레드크럼 매핑과 `apps/dashboard/components/WorkspaceSidebar.tsx`의 LNB 라벨을 `지식 공백`으로 바꾼다. **`aria-label`도 함께 바꾼다** — 보이는 이름만 고치면 스크린리더 사용자에게는 옛 명칭이 남는다.
  - Given: 멤버가 워크스페이스 셸에서 백로그 목적지를 참조하는 컨트롤을 본다
  - When: 내비게이션과 브레드크럼이 렌더링된다
  - Then: 보이는 라벨과 접근성 이름이 모두 `지식 공백`이다
- [x] 1.3 `apps/dashboard/components/PreviewWorkspace.tsx`에 혼재된 `미완성 백로그` · `작성 대기 백로그`를 같은 규칙으로 맞춘다. 미리보기는 실제 제품을 대표해야 하므로 명칭도 실제와 같아야 한다.
  - Given: 개발용 미리보기에서 백로그 목적지를 참조한다
  - When: 미리보기 내비게이션과 화면 제목이 렌더링된다
  - Then: 실제 제품과 같은 명칭을 쓴다
- [x] 1.4 홈 지식 그리드 섹션의 `지식 공백 (작성 대기 백로그)`는 그대로 둔다. 괄호는 기존 용어를 아는 사용자를 위한 보조 설명이며 앞머리가 정본 명칭이다.
  - Given: 멤버가 홈 지식 그리드를 본다
  - When: 백로그 섹션 제목이 렌더링된다
  - Then: 앞머리가 `지식 공백`이라 다른 목적지의 명칭과 이어진다

## 2. 테스트

- [x] 2.1 `apps/dashboard/tests/WorkspaceSidebar.test.tsx`의 `미완성 백로그` 단언을 새 명칭으로 고치고, 접근성 이름도 함께 검증한다.
  - Given: LNB 라벨이 바뀌었다
  - When: 해당 테스트를 실행한다
  - Then: 보이는 라벨과 `aria-label` 모두 새 명칭으로 단언된다
- [x] 2.2 옛 명칭 `미완성 백로그`가 `apps/dashboard` 소스와 테스트 어디에도 남아 있지 않은지 확인한다. 한 곳이라도 남으면 통일이 깨진 채 계약만 생긴다.
  - Given: 명칭 통일 작업이 끝났다
  - When: 저장소에서 옛 명칭을 검색한다
  - Then: 대시보드 소스·테스트에 옛 명칭이 없다

## 3. 검증 및 스펙 아카이브

- [x] 3.1 `pnpm --dir apps/dashboard test`, `typecheck`, `lint`와 `openspec validate backlog-vocabulary-unification --strict`를 새로 실행한다.
  - Given: 구현 task가 완료되었다
  - When: 필수 검증을 실행한다
  - Then: skip이나 실패를 성공으로 오인하지 않는다
- [x] 3.2 delta spec을 정본에 동기화하고 strict specs validation 후 change를 아카이브한다.
  - Given: 구현과 검증이 완료되었다
  - When: OpenSpec 동기화·아카이브 절차를 실행한다
  - Then: `dashboard-design-consistency` 정본이 목적지 명칭 계약을 보존한다

## 1. 워크스페이스 스위처 인라인 생성 폼

- [x] 1.1 "새 워크스페이스 생성" 항목을 `DropdownMenu.Item` + `Link`에서, 진입점 버튼과 인라인 폼을 로컬 state로 전환하는 평범한 컨테이너로 교체한다. 진입점 클릭은 메뉴를 닫지 않고 그 자리를 이름 입력 폼으로 바꾼다.
  - Given: 소속 워크스페이스가 3개 미만인 인증 사용자가 워크스페이스 스위처를 열었다.
  - When: "새 워크스페이스 생성"을 클릭 또는 키보드로 활성화한다.
  - Then: 드롭다운이 닫히지 않고 같은 자리가 이름 입력 필드 + 제출/취소로 바뀐다.
  - Verification: 먼저 Vitest로 진입점 클릭 시 폼 전환·드롭다운 유지·키보드 활성화를 작성한 뒤 `pnpm test -- --run`, `pnpm typecheck`, `pnpm lint`를 통과한다.

- [x] 1.2 인라인 폼 제출이 기존 `createPersonalWorkspace` 서버 액션을 그대로 호출하고, 성공 시 새 워크스페이스로 이동한다.
  - Given: 인라인 폼이 열려 있다.
  - When: 1~100자 이름을 제출한다.
  - Then: `createPersonalWorkspace`가 호출되고, 성공하면 반환된 workspaceId로 이동한다.
  - Verification: Vitest로 제출 시 서버 액션 호출 인자와 성공 시 라우팅을 확인한 뒤 `pnpm test -- --run`, `pnpm typecheck`, `pnpm lint`를 통과한다.

- [x] 1.3 서버 액션 실패(상한 도달·검증 오류·slug 충돌 등)를 인라인 폼 안에 표시하고, 입력값과 폼을 유지한다.
  - Given: 인라인 폼이 열려 있다.
  - When: 서버 액션이 오류를 반환한다(상한 도달 포함).
  - Then: 폼은 닫히지 않고 반환된 오류 문구를 그대로 표시하며, 입력값은 지워지지 않는다.
  - Verification: Vitest로 오류 응답 시 폼 유지·문구 노출을 확인한 뒤 `pnpm test -- --run`, `pnpm typecheck`, `pnpm lint`를 통과한다.

- [x] 1.4 취소 동작과, 드롭다운이 닫힐 때 폼 상태를 리셋하는 것을 구현한다.
  - Given: 인라인 폼이 열려 있고 사용자가 이름을 일부 입력했다.
  - When: 취소를 누르거나 드롭다운이 닫힌다.
  - Then: 입력값이 버려지고 다음에 열었을 때 진입점부터 다시 보여준다. 워크스페이스는 생성되지 않는다.
  - Verification: Vitest로 취소·재오픈 시 상태 리셋을 확인한 뒤 `pnpm test -- --run`, `pnpm typecheck`, `pnpm lint`를 통과한다.

- [x] 1.5 상한(3개) 도달 시 진입점 자체를 숨기는 기존 동작이 유지되는지 회귀 확인한다.
  - Given: 소속 워크스페이스가 이미 3개인 인증 사용자.
  - When: 워크스페이스 스위처를 연다.
  - Then: "새 워크스페이스 생성" 진입점이 렌더링되지 않는다(기존 `WorkspaceSwitcher.test.tsx` 커버리지 유지 확인).
  - Verification: 기존 테스트가 그대로 통과하는지 `pnpm test -- --run`으로 확인.

## 2. 스펙 동기화

- [x] 2.1 델타 스펙을 `openspec/specs/additional-workspace-creation/spec.md`에 반영한다.
  - Given: 구현과 테스트가 전부 통과했다.
  - When: `/opsx:sync`를 실행한다.
  - Then: 메인 스펙이 이 change의 MODIFIED/ADDED 요구사항을 반영하고 `openspec validate --specs`가 통과한다.
  - Verification: `openspec validate --specs` 통과.

## Why

`WorkspaceSwitcher`의 "새 워크스페이스 생성" 항목은 클릭하면 `/w/new`로 이동한다 — 드롭다운이 닫히고 페이지 전체가 전환된 뒤에야 이름을 입력할 수 있다. 이름 하나만 받으면 끝나는 동작치고 컨텍스트 전환 비용이 크다. 사용자가 직접 요청한 개선(checklists_v2.json UX-04)이며, 드롭다운을 닫지 않고 그 자리에서 입력받는 인라인 방식으로 마찰을 줄인다.

## What Changes

- `WorkspaceSwitcher`의 "새 워크스페이스 생성" 항목을 클릭하면 같은 자리가 이름 입력 폼으로 바뀐다. 제출하면 기존 `createPersonalWorkspace` 서버 액션을 그대로 호출하고, 성공 시 새 워크스페이스로 이동한다.
- 상한(3개) 도달 시 인라인 항목 자체를 숨긴다 — `WorkspaceSwitcher`가 이미 `/w/new` 링크에 적용 중인 규칙(`workspaces.length < 3`)과 동일하게, 서버 액션의 재검증도 그대로 최종 방어선으로 남는다.
- `/w/new` 라우트는 그대로 둔다 — 직접 URL 접근·북마크·`additional-workspace-creation` 스펙의 "소속 개수와 무관한 전용 라우트" 요구사항을 건드리지 않는다. 인라인 입력은 그 요구사항을 대체하는 게 아니라 같은 생성 흐름에 더해지는 두 번째 진입점이다.

## Capabilities

### Modified Capabilities

- `additional-workspace-creation`: 기존 "소속 개수와 무관한 전용 라우트" 요구사항은 그대로 두고, `WorkspaceSwitcher`에서 인라인으로 생성하는 새 요구사항을 추가한다.

## Impact

- `apps/dashboard/components/WorkspaceSwitcher.tsx` — "새 워크스페이스 생성" 항목을 Link에서 인라인 폼 토글로 교체.
- 서버 액션(`apps/dashboard/app/onboarding-actions.ts`의 `createPersonalWorkspace`)은 재사용하며 변경하지 않는다 — 이름 검증·slug 충돌 재시도·3개 상한 재검증 로직은 이미 존재한다.
- `/w/new` 라우트(`apps/dashboard/app/w/new/page.tsx`)는 변경하지 않는다.

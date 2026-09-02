## Why

미해결 레드링크를 모아 보여 주는 목적지가 화면마다 다른 이름으로 불린다.

| 위치 | 현재 명칭 |
| --- | --- |
| 홈 지식 그리드 섹션 | `지식 공백 (작성 대기 백로그)` |
| 전용 화면 `h1` | `미완성 백로그` |
| 브레드크럼 | `미완성 백로그` |
| LNB 내비게이션 | `미완성 백로그` |
| 개발용 미리보기 | `미완성 백로그` · `작성 대기 백로그` 혼재 |

`dashboard-design-consistency`의 `Shared state and control language`가 "한 상태를 두 목적지에서 다르게 부르지 않는다"를 요구하지만, 그 요구사항은 **상태 값**에 한정돼 있어 목적지·섹션 명칭에는 닿지 않는다. 어떤 스펙도 이 명칭을 고정하지 않아 화면이 늘어날 때마다 새 이름이 하나씩 붙었다.

이 제품의 핵심 가치는 원문과 위키 양쪽으로 추적 가능한 답변이다. 그 추적을 완성하려면 사용자가 "아직 원문이 없는 자리"를 인지하고 메워야 하는데, 그 자리를 부르는 이름이 화면마다 다르면 같은 작업 흐름인 줄 모른다.

## What Changes

목적지 명칭을 **`지식 공백`** 하나로 통일한다.

- 전용 화면 `h1`, 브레드크럼, LNB 내비게이션 라벨을 `지식 공백`으로 바꾼다
- 홈 지식 그리드 섹션은 `지식 공백 (작성 대기 백로그)` 형태를 유지한다 — 괄호는 기존 용어를 아는 사용자를 위한 보조 설명이며, 앞머리가 정본 명칭이라 통일을 깨지 않는다
- 개발용 미리보기의 혼재된 명칭도 같은 규칙으로 맞춘다
- 명칭을 `dashboard-design-consistency`의 계약으로 고정해, 다음 화면이 또 새 이름을 붙이지 못하게 한다

라우트(`/w/[workspaceId]/backlog`), 데이터, 필터·검색 동작은 바뀌지 않는다. 화면에 보이는 문구만 바뀐다.

## Capabilities

### New Capabilities

없음.

### Modified Capabilities

- `dashboard-design-consistency`: 목적지 명칭에도 단일 어휘를 요구하도록 `Shared state and control language`를 확장한다. 현재 이 요구사항은 상태 값에만 적용된다.

## Impact

- `apps/dashboard/components/BacklogList.tsx` — 전용 화면 `h1`
- `apps/dashboard/components/WorkspaceShell.tsx` — 브레드크럼 매핑
- `apps/dashboard/components/WorkspaceSidebar.tsx` — LNB 라벨과 `aria-label`
- `apps/dashboard/components/PreviewWorkspace.tsx` — 미리보기 내비게이션·화면 제목
- `apps/dashboard/tests/WorkspaceSidebar.test.tsx` — 라벨 단언

API·스키마·RLS·라우트 변경은 없다. `aria-label`이 함께 바뀌므로 스크린리더 사용자에게도 같은 이름이 전달된다.

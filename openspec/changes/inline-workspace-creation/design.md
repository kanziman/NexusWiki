## Context

`WorkspaceSwitcher.tsx`는 Radix `DropdownMenu`로 구현돼 있다. "새 워크스페이스 생성"은 현재 `DropdownMenu.Item` 안의 `<Link href="/w/new">`다 — Radix의 기본 동작상 `Item`을 선택(클릭/Enter)하면 메뉴가 자동으로 닫힌다. 인라인 폼으로 바꾸려면 이 자동 닫힘을 진입점 클릭 시점에는 켜두되(진입점 자체는 폼으로 전환될 뿐 메뉴는 열려 있어야 한다) 폼 내부 클릭·타이핑으로는 메뉴가 닫히지 않아야 한다.

동일한 생성 로직(`createPersonalWorkspace` 서버 액션 — 이름 검증, slug 충돌 재시도, 3개 상한 재검증)은 `/w/new` 라우트가 이미 쓰고 있고 그대로 재사용한다(proposal.md 참조).

## Goals / Non-Goals

**Goals:** 드롭다운을 닫지 않고 진입점 → 인라인 입력 폼 전환. 기존 서버 액션·검증·상한 로직 재사용. 상한 도달 시 진입점 숨김(기존 동작 유지).

**Non-Goals:** `/w/new` 라우트 변경. 서버 액션 로직 변경. 워크스페이스 스위처 외 다른 화면에 같은 인라인 패턴 적용(범위 밖).

## Decisions

### ADR-1: 진입점을 `DropdownMenu.Item`에서 일반 `<div>` 래퍼로 바꾼다

**Context:** `DropdownMenu.Item`은 선택 시 `onSelect`가 끝나면 메뉴를 자동으로 닫는다(Radix 기본 동작). 인라인 폼은 메뉴가 열린 채로 그 자리에서 입력을 받아야 한다.

**Decision:** "새 워크스페이스 생성" 항목을 `DropdownMenu.Item`이 아니라 그 안에 진입점 버튼(또는 인라인 폼)을 직접 렌더링하는 평범한 `<div>`로 바꾼다. 진입점 버튼 클릭은 로컬 state(`mode: "idle" | "creating"`)만 바꾸고 Radix에 선택 이벤트를 보내지 않는다 — 그래서 메뉴가 안 닫힌다.

**Alternatives:** `DropdownMenu.Item`에 `onSelect={(e) => e.preventDefault()}`를 걸어 자동 닫힘만 막는 방법도 있었다. 그러나 `Item`은 포커스·roving tabIndex를 메뉴 자체가 관리해, 안에 `<input>`을 두면 타이핑 중 방향키 등이 메뉴 내비게이션과 충돌한다(Radix 이슈로 알려진 패턴). 평범한 `<div>`가 이 충돌을 원천적으로 피한다.

**Consequences:** 진입점 버튼 자체는 keyboard-focusable해야 하므로(`<button>`) Radix의 자동 roving tabIndex 밖에서 수동으로 그 역할을 한다 — 기존 `Item`들과 Tab 순서상 자연스럽게 이어지는지 구현 시 확인.

### ADR-2: 상태는 `WorkspaceSwitcher` 컴포넌트 로컬에 둔다

**Context:** 인라인 폼의 열림/닫힘·제출 중·오류 상태는 이 컴포넌트 밖 어디에서도 필요하지 않다.

**Decision:** `useState`로 `mode`, `name`, `pending`, `error`를 관리한다. 드롭다운이 닫히면(외부 클릭 등 Radix 기본 동작) `onOpenChange`에서 이 상태를 `idle`로 리셋한다 — 다음에 열었을 때 이전 입력이 남아있지 않도록.

**Alternatives:** 없음 — 범위가 이 컴포넌트를 벗어나지 않는다.

### ADR-3: 인라인 폼도 `createPersonalWorkspace`를 그대로 호출한다

**Context:** `/w/new` 라우트의 `WorkspaceOnboarding` 컴포넌트가 이미 이 서버 액션을 호출한다.

**Decision:** 인라인 폼 제출도 같은 `createPersonalWorkspace(name)` 서버 액션을 호출한다. 성공하면 반환된 `workspaceId`로 `router.push`. 실패하면 서버가 반환한 에러 문구를 폼 안에 그대로 표시한다(3개 상한 문구 포함 — 별도 문구를 만들지 않는다).

**Alternatives:** 새 서버 액션을 만드는 방법은 검증·상한·slug 재시도 로직을 중복시킨다 — 하나의 진실 소스가 아니게 된다.

## Risks / Trade-offs

- [Radix `Item` → `div` 전환이 기존 키보드 내비게이션(방향키로 항목 이동)을 깰 수 있다] → 구현 후 Tab/방향키로 전체 메뉴를 훑어 진입점 버튼까지 자연스럽게 도달하는지 수동 확인. 테스트에도 키보드 활성화 케이스 포함.
- [드롭다운이 열린 채로 다른 탭에서 상한에 도달하면 인라인 폼이 낙관적으로 남아있을 수 있다] → 서버 액션이 최종 판정이므로 제출 시점에 거부되고 오류가 표시된다(스펙 시나리오 "인라인 폼 제출 시점에 상한에 도달해 있으면"). 데이터 정합성 문제는 없다 — UX상 한 번의 재시도만 더 필요하다.

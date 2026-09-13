## Why

홈 Ask 히어로의 검색 범위 선택(`워크스페이스 전체` · `카테고리 한정` · `현재 문서 주변`)은 화면에서만 고를 수 있다. 질문하기 화면은 `scope` 쿼리를 읽지 않고, Ask API에도 범위 필드가 없으며, 기본 검색 정책은 `graph_enabled = false`라 hop으로 범위를 좁히지 않는다. 고를 수 있는데 결과가 같으면 범위가 바뀐 것처럼 보인다.

## What Changes

- 홈 Ask 히어로에서 검색 범위 선택 컨트롤을 제거한다
- 질문 제출은 질의만 `/ask?q=`로 넘긴다. `scope` 쿼리를 붙이지 않는다
- `workspace-home-dashboard`의 Ask 히어로 계약을 실제 검색(워크스페이스 전체)에 맞춘다

지식 그래프 화면의 이웃 표시는 질문 범위가 아니므로 유지한다.

## Capabilities

### New Capabilities

없음.

### Modified Capabilities

- `workspace-home-dashboard`: Ask 히어로에서 검색 범위 선택과 `scope` 쿼리 전달을 제거하고, 질문은 워크스페이스 전체 검색으로만 시작한다

## Impact

- `apps/dashboard/components/AskHero.tsx` — 범위 메뉴 상태·제출 쿼리 제거
- `apps/dashboard/tests/AskHero.test.tsx` — 범위 메뉴 단언 제거, 제출은 `q`만 남긴다
- `apps/dashboard/app/w/[workspaceId]/loading.tsx` — 범위 자리 스켈레톤 제거
- `docs/design-systems/v2/nexuswiki-design-system.css` · `nexuswiki-workspace-home.html` — 범위 컨트롤 마크업·스타일 제거
- `docs/design-systems/v2/PRODUCT-INVARIANTS.md` · `workspace-home-prd.md` — 스코프 셀렉터 서술 정리

API·스키마·RLS·검색 정책은 바꾸지 않는다.

## Why

`openspec/specs/graph-surface-separation/spec.md`는 그래프 카테고리 컨트롤과 캔버스가 spacing/boundary/surface treatment로 시각 분리되어야 한다고 이미 규정하고 있고, 관련 change(`archive/2026-08-13-separate-graph-control-canvas`)도 tasks 전부 완료 표시로 archive되어 있다. 하지만 실제 코드(`apps/dashboard/components/GraphCanvas.tsx`)는 이 archive 이후에도 캔버스 wrapper에 배경이 전혀 없어 필터 섹션과 흰색으로 동일하게 렌더된다. 원인은 `apps/dashboard/app/globals.css`가 `docs/design-systems/design-tokens.css`(Airbnb 스타일 토큰)에서 끌어온 `--color-canvas`(#ffffff, Tailwind `bg-canvas` 유틸로 노출)와, 컴포넌트가 직접 쓰는 `--nw-surface`(#ffffff, arbitrary-value)가 우연히 같은 흰색으로 겹치기 때문이다. Linear HHH-19가 바로 이 증상을 가리킨다.

## What Changes

- `apps/dashboard/components/GraphCanvas.tsx`의 캔버스 wrapper에 현재 미사용인 `--nw-canvas`(#fcfcfa)를 배경으로 부여해, 필터 섹션(`--nw-surface`, #ffffff)과 명도 차이를 만든다.
- 기존 접근성 라벨(`aria-label="지식 그래프"`)은 그대로 유지한다 — 스펙이 이미 요구하는 부분이라 변경 없음.

**스코프 축소 기록**: 최초 초안은 `globals.css`의 `@theme` 블록(Airbnb `design-tokens.css` 유래 `--color-*`)을 `--nw-*`로 통째 alias하는 안을 포함했다. 실제 값을 대조한 결과 `--color-canvas`(#ffffff)는 `--nw-surface`와 동일해 무해하지만, `--color-primary`(`#ff385c`, Airbnb Rausch red)는 `apps/dashboard/components/{LoginForm,OperationsPanel,GraphLensFilter,CitationMarker,AskConversation,MembersList,InviteForm,WikiPageContent,SettingsMembersPanel}.tsx` 9곳에서 `bg-primary`/`text-primary`로 실사용 중이며 `--nw-action`(#171717, 검정)과 값이 다르다. 이걸 이번 change에 포함시키면 그래프 페이지 버그 수정 범위를 벗어나 앱 전체 primary 버튼 색이 빨강→검정으로 바뀌는 대규모 부작용이 생긴다. 이번 change에서는 제외하고 별도 change로 분리한다 (design.md 참고).

## Capabilities

### New Capabilities

없음.

### Modified Capabilities

없음 — `graph-surface-separation` 요구사항 문구 자체는 이미 정확하며 바뀌지 않는다. 이번 change는 그 요구사항을 실제로 충족시키는 구현 갭만 닫는다 (`.openspec.yaml`에 `skip_specs: true` 선언).

## Impact

- `apps/dashboard/app/globals.css`, `apps/dashboard/components/GraphCanvas.tsx` — 시각적 변경만, 그래프 쿼리·노드 상호작용 로직은 변경 없음.
- Linear HHH-19 (id `30f162fd-a794-4ee1-8370-d8ac73a88825`).

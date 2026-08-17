## Context

`apps/dashboard/app/globals.css`는 두 개의 색 토큰 소스를 동시에 갖고 있다: `@theme` 블록이 `docs/design-systems/design-tokens.css`(Airbnb 스타일 팔레트)에서 `--color-canvas`/`--color-primary`/`--color-ink` 등 Tailwind named 유틸(`bg-canvas`, `text-ink`, ...)을 만들고, 별도로 순수 `:root` 블록이 `--nw-*`(quiet editorial, `dashboard-ui-spec.md`의 실제 소스) 값을 정의한다. 컴포넌트들은 두 체계를 섞어 쓴다 — `GraphLensFilter.tsx`는 Tailwind named 유틸(`bg-canvas`), `graph/page.tsx`의 섹션 wrapper와 `GraphCanvas.tsx`는 `--nw-*`를 arbitrary-value로 쓴다. 두 체계가 `#ffffff`로 우연히 일치해 HHH-19 증상이 발생한다. See proposal.md - Why.

## Goals / Non-Goals

**Goals:**
- 그래프 캔버스에 필터 섹션과 구분되는 배경을 부여한다 — 이 change가 손대는 유일한 시각 변화.

**Non-Goals:**
- `--color-*`(Airbnb `design-tokens.css` 유래) ↔ `--nw-*` 토큰 체계 통합. 값을 직접 대조해보니 `--color-canvas`(#ffffff)는 무해하지만 `--color-primary`(#ff385c, Airbnb Rausch red)는 9개 컴포넌트가 `bg-primary`/`text-primary`로 실사용 중이고 `--nw-action`(#171717, 검정)과 값이 다르다 — 앱 전체 primary 버튼 색을 바꾸는 별도의, 훨씬 큰 범위의 결정이라 이 change에서 제외한다. 아래 Risks 참고.
- 그래프 쿼리·필터 로직, 카테고리 목록 변경.

## Decisions

- **새 토큰을 만들지 않고 기존 미사용 토큰 재활용**: 캔버스 배경에 새 CSS 변수를 만드는 대신 이미 정의돼 있지만 어디서도 안 쓰이던 `--nw-canvas`(#fcfcfa)를 그대로 쓴다. `impeccable` product register의 "second neutral layer" 권고와도 일치.
- **globals.css의 `--color-*`/`--nw-*` 이중 토큰 체계는 건드리지 않는다**: HHH-19는 `GraphCanvas.tsx`에 배경이 아예 없어서 생기는 문제이지, 두 토큰 체계가 충돌해서 생기는 문제가 아니다(둘 다 우연히 흰색이라 지금은 무해하게 겹쳐 있을 뿐). 토큰 통합은 `dashboard-design-consistency` 스펙("Primary actions ... SHALL use the same visual hierarchy")이 이미 요구하고 있고, 이미 archive된 `2026-08-13-unify-dashboard-design-system`가 이 요구를 충족했다고 표시돼 있지만 실제로는(빨강 vs 검정 primary 공존) 충족되지 않았다 — 이것도 별도 후속 change 대상이다.

## Risks / Trade-offs

- [Risk] 이번 change 이후에도 `--color-*`/`--nw-*` 이중 체계와 primary 색상 불일치는 그대로 남는다 → Mitigation: 범위를 명시적으로 Non-Goals에 기록하고, 별도 change(가칭 `unify-primary-action-color`)로 사용자에게 보고한다. 이 change의 완료가 그 문제까지 해결한 것으로 오인되지 않도록 proposal.md에도 스코프 축소를 기록해 둔다.

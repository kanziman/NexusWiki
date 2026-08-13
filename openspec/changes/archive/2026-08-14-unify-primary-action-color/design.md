## Context

`globals.css`의 `@theme` 블록은 `--color-primary: var(--color-primary);` 같은 자기참조 문법으로 `docs/design-systems/design-tokens.css`(Airbnb 파일, `@import`로 들어옴)의 값을 그대로 Tailwind 유틸에 노출한다. `--nw-action`(#171717)은 `.nw-action` 클래스 전용으로 별도 존재한다. See proposal.md - Why.

## Goals / Non-Goals

**Goals:**
- `bg-primary`/`text-primary`/`border-primary`/`bg-primary-active`/`bg-primary-disabled` Tailwind 유틸이 `.nw-action`과 같은 톤을 내도록 토큰만 재배선한다.

**Non-Goals:**
- `--color-primary-error-text`(폼 에러 텍스트) — 브랜드 primary와 무관한 별도 시맨틱, 손대지 않는다.
- `docs/design-systems/design-tokens.css`(Airbnb 파일) 자체를 정리·삭제하는 일 — 여전히 다른 유틸(`bg-canvas`, `text-ink` 등)의 소스이고, `complete-graph-surface-separation`에서도 같은 이유로 스코프 밖으로 뒀다.
- 컴포넌트 파일 수정 — 전부 named Tailwind 유틸을 쓰므로 필요 없다.

## Decisions

- **`--color-primary-disabled` 매핑**: `.nw-action:disabled`는 배경색을 바꾸지 않고 `opacity: 0.42`만 적용한다. `bg-primary-disabled`는 (opacity가 아니라) 리터럴 배경색 유틸이라 같은 시각 효과를 내려면 `color-mix(in srgb, var(--nw-action) 42%, white)`로 근사한다 — 임의의 새 값을 만들지 않고 기존 0.42 비율을 그대로 재사용.
- **`--color-on-primary`는 변경하지 않는다**: 이미 `#ffffff`로 `.nw-action`의 `color: #fff`와 동일한 값이라 재배선할 이유가 없다.

## Risks / Trade-offs

- [Risk] 앱 전체에서 눈에 띄는 시각적 변화(빨강→검정)라 사용자가 원치 않는 부분이 있을 수 있음 → Mitigation: `dashboard-ui-spec.md`(이미 커밋된 quiet editorial 스펙)와 `dashboard-design-consistency` 스펙이 둘 다 이미 이 방향을 명시하고 있고, HHH-21 이슈로 사용자가 직접 이 change를 요청했다.

## Why

`dashboard-design-consistency` 스펙은 "Primary actions ... SHALL use the same visual hierarchy across destinations"를 요구하지만, 실제로는 `apps/dashboard/app/globals.css`의 `@theme` 블록이 `--color-primary`(Airbnb `design-tokens.css` 유래, `#ff385c` 빨강)를 Tailwind `bg-primary`/`text-primary`/`border-primary`/`text-on-primary`/`bg-primary-active`/`bg-primary-disabled` 유틸로 노출하고 있어, 15개 컴포넌트(LoginForm, AskConversation, WikiPageContent, GraphLensFilter, CitationMarker, MembersList, InviteForm, OperationsPanel, SettingsMembersPanel, JobStepper, RedLinkCta, WorkspaceSwitcher, CitationSidePanel, GraphCanvas, DashboardPrimitives)가 빨간 primary 버튼/링크/보더를 렌더한다. `dashboard-ui-spec.md`(quiet editorial 스펙)가 실제로 지정한 primary 색은 `.nw-action`(검정 `#171717`)이고 이건 Dropzone·워크스페이스 홈 등 3곳에만 쓰인다. Linear HHH-21.

이미 archive된 `2026-08-13-unify-dashboard-design-system` change의 task 2.1("Consolidate semantic tokens")이 완료로 표시돼 있었지만, 실제로는 두 색상 체계가 그대로 병존한 채 남아있었다(HHH-18/19와 같은 패턴).

## What Changes

- `apps/dashboard/app/globals.css`의 `@theme` 블록에서 `--color-primary`/`--color-primary-active`/`--color-primary-disabled`를 `--nw-action`/`--nw-action-hover`/그에 준하는 옅은 톤으로 alias한다. `--color-on-primary`(`#ffffff`)는 이미 `.nw-action`의 `color: #fff`와 값이 같아 변경하지 않는다.
- 컴포넌트 15곳은 **한 곳도 수정하지 않는다** — 전부 named Tailwind 유틸(`bg-primary` 등)을 쓰고 있어 토큰 재배선만으로 자동 반영된다.
- `--color-primary-error-text`(폼 인라인 에러 텍스트, `#c13515`)는 이 change의 스코프 밖이다 — 브랜드 primary 색과 무관한 별도 시맨틱(에러)이라 손대지 않는다.

## Capabilities

### New Capabilities

없음.

### Modified Capabilities

없음 — `dashboard-design-consistency`의 "Primary actions ... SHALL use the same visual hierarchy" 요구사항 문구는 이미 정확하며 바뀌지 않는다. 이번 change는 그 요구사항을 실제로 충족시키는 구현 갭만 닫는다 (`.openspec.yaml`에 `skip_specs: true` 선언).

## Impact

- `apps/dashboard/app/globals.css`만 수정 — 앱 전체에서 빨간 primary 버튼/링크/보더가 검정(`.nw-action`과 동일한 톤)으로 바뀌는 시각적 변경. 기능/로직 변경 없음.
- Linear HHH-21 (id `c0ba26d8-d048-406e-9b60-994f0641d8e5`).

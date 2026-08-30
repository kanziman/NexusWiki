## Why

미인증 방문자가 제품 가치를 확인할 공개 진입점과 라이브 쇼케이스 초안은 만들어졌지만, 모바일 탐색·상호작용 접근성·반응형 밀도·마케팅 문구 정확성·회귀 테스트가 출시 가능한 수준으로 마감되지 않았다. 인증 사용자 진입 흐름은 그대로 보존하면서 공개 홈을 제품의 이중 인용 가치를 직접 이해할 수 있는 안정적인 랜딩으로 완성해야 한다.

## What Changes

- 미인증 `/` 방문자에게 공개 랜딩을 제공하고, 인증 사용자의 기존 워크스페이스 선택·온보딩·자동 진입 흐름을 유지한다.
- 데스크톱과 모바일에서 헤더 탐색, CTA, 라이브 쇼케이스, 활용 사례, FAQ가 가로 넘침 없이 동작하도록 반응형 레이아웃을 보완한다.
- 쇼케이스 선택 상태와 FAQ 열림 상태를 키보드·스크린리더가 이해할 수 있게 상태·관계 속성을 제공한다.
- 중복 마크업과 불필요한 장식 패턴을 제거하고, 제품이 실제로 보장하는 원문·위키 이중 인용과 RLS 격리 범위에 맞춰 문구를 정리한다.
- 공개 홈 분기와 핵심 랜딩 상호작용을 회귀 테스트로 고정한다.

## Capabilities

### New Capabilities

- `public-marketing-landing`: 미인증 공개 홈의 라우팅, 반응형 탐색, 라이브 쇼케이스, 접근 가능한 FAQ와 전환 경로를 정의한다.

### Modified Capabilities

- 없음.

## Impact

- 대시보드 공개 홈: `apps/dashboard/app/page.tsx`, `apps/dashboard/middleware.ts`
- 랜딩 UI: `apps/dashboard/components/PublicLandingPage.tsx`
- 회귀 테스트: `apps/dashboard/tests/workspace-entry-route.test.tsx`, `apps/dashboard/tests/middleware-auth.test.ts`, 신규 랜딩 컴포넌트 테스트
- 시각 기준 문서: `docs/design-systems/v2/nexuswiki-public-landing.html`
- 백엔드 API, 데이터베이스 스키마, 인증된 워크스페이스 화면에는 변경이 없다.

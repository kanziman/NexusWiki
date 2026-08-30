## 1. 공개 홈과 반응형 전환 경로를 마감한다

- [x] 1.1 미인증 루트 분기와 인증 사용자 진입 계약을 보존하면서 랜딩 헤더를 표시 컴포넌트로 분리하고, 모바일 메뉴·CTA·감소 모션·정확한 제품 문구를 적용한다. (GitHub sub-issue: https://github.com/kanziman/NexusWiki/issues/98)
  - Given: 미인증 방문자는 공개 홈을 보고 인증 사용자는 기존 워크스페이스 진입 흐름을 사용한다.
  - When: 방문자가 데스크톱 또는 모바일에서 헤더와 히어로의 탐색·로그인·시작 CTA를 사용한다.
  - Then: 가로 넘침 없이 동일한 주요 경로를 사용할 수 있고, 키보드 포커스와 모바일 메뉴 확장 상태가 노출되며, 보호된 `/w/` 경로는 계속 로그인으로 이동한다.
  - Verification: `cd apps/dashboard && pnpm exec vitest run tests/PublicLandingPage.test.tsx tests/workspace-entry-route.test.tsx tests/middleware-auth.test.ts`, `cd apps/dashboard && pnpm typecheck && pnpm lint`

## 2. 쇼케이스와 FAQ의 검증 가능한 상호작용을 마감한다

- [x] 2.1 정적 콘텐츠와 쇼케이스·FAQ 표시를 분리하고, 현재 선택·결과 갱신·FAQ 관계를 보조 기술에 노출하며 중복·장식 마크업을 정리한다. (GitHub sub-issue: https://github.com/kanziman/NexusWiki/issues/99)
  - Given: 공개 랜딩에 개인 전문가 위키와 팀 정책 위키 시나리오, 추천 질문, FAQ가 있다.
  - When: 방문자가 워크스페이스와 추천 질문을 전환하거나 FAQ를 열고 닫는다.
  - Then: 질문·답변·원문·위키 근거가 함께 갱신되고 선택·확장 상태가 키보드와 스크린리더에 전달되며, 기존 시각 계층은 유지된다.
  - Verification: `cd apps/dashboard && pnpm exec vitest run tests/PublicLandingPage.test.tsx`, `cd apps/dashboard && pnpm typecheck && pnpm lint`, `openspec validate polish-public-landing-page --strict`

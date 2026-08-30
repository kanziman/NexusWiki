## 1. 회원가입 화면 2단 split 디자인 통일

- [x] 1.1 `/signup` 화면을 2단 Split 레이아웃으로 변경하고, `LoginForm`에 `presentation="signup"`을 추가하여 가입 타이틀과 Google 시작 버튼을 제공한다. (GitHub sub-issue: https://github.com/kanziman/NexusWiki/issues/102)
  - Given: 미인증 사용자가 `/signup` 경로에 접근한다.
  - When: 데스크톱 또는 모바일 환경에서 화면을 확인한다.
  - Then: 2단 Split 비주얼과 "나만의 지식 자산을 시작하세요" 타이틀, "Google 계정으로 시작하기" CTA, 로그인 전환 링크가 가로 넘침 없이 렌더링된다.
  - Verification: `cd apps/dashboard && pnpm exec vitest run tests/signup-page-route.test.tsx tests/LoginForm.test.tsx`, `cd apps/dashboard && pnpm typecheck && pnpm lint`

## 2. 루트 경로 OAuth code 자동 포워딩 및 회귀 검증

- [x] 2.1 `middleware.ts`에 `/?code=...` 요청을 `/auth/callback?code=...` 로 전달하는 안전 가드를 추가하고 관련 테스트를 작성한다. (GitHub sub-issue: https://github.com/kanziman/NexusWiki/issues/103)
  - Given: 브라우저가 OAuth 인증 후 `/?code=auth-code-123` 형식의 쿼리로 루트에 접근한다.
  - When: 미들웨어가 요청을 처리한다.
  - Then: 쿼리 파라미터를 유지한 채 `/auth/callback?code=auth-code-123` 로 307 리다이렉트되어 세션 교환이 완료된다.
  - Verification: `cd apps/dashboard && pnpm exec vitest run tests/middleware-auth.test.ts`, `openspec validate unify-auth-split-and-fallback --strict`

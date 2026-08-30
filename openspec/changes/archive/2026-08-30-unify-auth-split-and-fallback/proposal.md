## Why

로그인 페이지는 2단 Split 화면으로 전면 개편되었으나 `/signup` 가입 페이지가 여전히 구형 흰색 폼으로 남아 있어 브랜드 경험이 단절되고, OAuth 콜백 도메인/경로 오설정 시 `/?code=...` 로 진입했을 때 세션 교환이 누락되어 비로그인 상태로 튕기는 문제가 발생한다. 가입 화면의 Split 디자인을 일원화하고 루트 경로의 OAuth authorization code 폴백 가드를 추가해 인증 신뢰성을 완성해야 한다.

## What Changes

- `/signup` 화면을 `/login`과 동일한 2단 Split 화면(지식 비주얼, 시나리오 프리뷰, Google 시작 버튼, 로그인 이동 링크)으로 일원화한다.
- `LoginForm`에 가입 모드(`signup`) 프레젠테이션을 지원하여 "Google 계정으로 시작하기" 라벨과 상태를 제공한다.
- 루트(`/`) 및 미들웨어에서 URL 쿼리에 `code` 파라미터가 포함되어 유입되는 경우, 이를 `/auth/callback?code=...` 로 자동 포워딩하여 세션 교환이 반드시 완료되도록 폴백 가드를 추가한다.
- 가입 화면 렌더링, 상호작용 및 OAuth 루트 코드 포워딩 회귀 테스트를 추가한다.

## Capabilities

### New Capabilities

- 없음.

### Modified Capabilities

- `google-authentication`: 가입 화면의 2단 Split 화면 제공 계약 및 루트 경로 OAuth code 자동 포워딩 폴백 요구사항을 추가한다.

## Impact

- 가입/로그인 라우트: `apps/dashboard/app/(auth)/signup/page.tsx`, `apps/dashboard/app/(auth)/login/page.tsx`
- 인증 폼 및 미들웨어: `apps/dashboard/components/LoginForm.tsx`, `apps/dashboard/middleware.ts`, `apps/dashboard/app/page.tsx`
- 회귀 테스트: `apps/dashboard/tests/signup-page-route.test.tsx`, `apps/dashboard/tests/middleware-auth.test.ts`, `apps/dashboard/tests/LoginForm.test.tsx`

## Context

See proposal.md - Why.

현재 대시보드는 `/login`에 `LoginHeroTitle`, `LoginKnowledgePreview`, `LoginForm`을 조합한 2단 Split 레이아웃을 사용하고 있다. 반면 `/signup`은 구형 레이아웃을 사용하고 있으며, Google OAuth 단일 인증 특성상 가입과 로그인의 기능 차이가 없음에도 사용자 경험이 분절되어 있다. 또한 Supabase 대시보드의 Redirect URLs 설정이 미비할 경우 `/?code=...` 로 반환된 authorization code가 처리되지 못하고 버려지는 문제가 존재한다.

## Goals / Non-Goals

**Goals:**
- `/signup` 화면을 `/login`과 동일한 2단 Split 시각 디자인으로 통일하고, 가입 전용 문구와 로그인 화면 링크를 제공한다.
- `LoginForm`에 `presentation="signup"`을 추가하여 "Google 계정으로 시작하기" CTA 및 접근성을 제공한다.
- `middleware.ts`에서 루트 경로(`/`)에 `code` 파라미터가 포함되어 유입되는 경우 `/auth/callback`으로 자동 리다이렉트하는 안전망을 구축한다.

**Non-Goals:**
- 이메일/비밀번호 등 Google 외의 추가 인증 공급자 도입.
- 데이터베이스 스키마나 백엔드 API 변경.

## Decisions

### ADR-1: Split Auth 레이아웃 재사용 및 가입 모드 프레젠테이션
- **선택:** `/signup` 페이지에서도 기존 `login-page` CSS 클래스와 `LoginHeroTitle`, `LoginKnowledgePreview`, `LoginForm`을 그대로 활용하고, 텍스트(Kicker: `GET STARTED`, Title: `나만의 지식 자산을<br />시작하세요.`, CTA: `Google 계정으로 시작하기`, 하단 전환 링크: `이미 계정이 있으신가요? 로그인하기`)를 가입 컨텍스트에 맞게 렌더링한다.
- **대안 고려:**
  1. *별도 SignUp 컴포넌트 및 CSS 클래스 신설*: 코드 중복이 발생하고 향후 인증 테마 수정 시 유지보수 비용이 증가함.
  2. */signup을 /login으로 301/302 단순 리다이렉트*: 스펙의 `/signup` 라우트 계약 및 명시적인 가입 전환 CTA와의 정합성이 떨어짐.
- **근거:** 단일 CSS 스타일과 검증된 시각 프리뷰 컴포넌트를 공유하면서도 사용자에게 가입에 특화된 문맥을 제공할 수 있다.

### ADR-2: 미들웨어 레벨의 OAuth 루트 코드 포워딩
- **선택:** `middleware.ts`에서 `pathname === "/"`이고 `request.nextUrl.searchParams.has("code")`인 경우, `request.nextUrl.clone()`으로 전체 쿼리스트링을 보존한 뒤 pathname을 `/auth/callback`으로 변경하여 `NextResponse.redirect`를 반환한다.
- **대안 고려:**
  1. *`app/page.tsx` 서버 컴포넌트 내에서 searchParams 확인 후 redirect*: 미들웨어보다 늦게 실행되며 React 서버 컴포넌트 렌더링 오버헤드가 발생함.
  2. *클라이언트 컴포넌트에서 감지*: 페이지가 번들링되어 로드된 후에야 동작하므로 화면 깜빡임과 인증 지연이 발생함.
- **근거:** 미들웨어에서 처리하면 불필요한 페이지 렌더링 없이 즉시 `/auth/callback`으로 진입하여 세션을 교환하므로 가장 빠르고 안전하다.

## Risks / Trade-offs

- **[Risk]** `code` 외에 `next`, `error` 등 다른 쿼리 파라미터가 유실될 위험
  - **Mitigation**: `request.nextUrl.clone()`을 사용하여 searchParams 전체를 그대로 유지한 채 pathname만 `/auth/callback`으로 교체한다.

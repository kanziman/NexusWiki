# Spec Conformance Review — r2

## 판정

**pass**

## 검토 범위

- delta: `specs/google-authentication/spec.md`의 `Google 단일 인증`
- 구현: `/login`, `LoginForm`, OAuth 콜백 및 로그인 전용 반응형 스타일
- r1 후속 수정: 데스크톱 인증 패널의 제품명 제공 여부

## r1 지적 사항 확인

r1에서 지적한 인증 영역 내부 제품명 누락은 해소됐다. 로그인 인증 패널의
`login-auth-card` 첫 요소가 마크와 `NexusWiki` 텍스트를 상시 렌더링한다
(`apps/dashboard/app/(auth)/login/page.tsx:59-69`). 이는 데스크톱에서 숨겨지는
시각 보조 영역과 독립적인 인증 영역의 제품명이며, `.login-auth-brand`에는
데스크톱·모바일 어느 쪽에서도 이를 감추는 규칙이 없다
(`apps/dashboard/app/globals.css:417-425`).

## delta 시나리오 대조

| delta 시나리오 | 결과 | 근거 |
| --- | --- | --- |
| 로그인 시작 | 충족 | `LoginForm`은 Google provider와 내부 `/auth/callback?next=/` redirect 대상으로 OAuth를 시작한다 (`components/LoginForm.tsx:34-40`). |
| 인증 실패 | 충족 | 콜백은 코드 교환 실패 시 `/login?error=auth`로 이동하고 (`app/auth/callback/route.ts:29-35`), 로그인 페이지와 폼은 이를 계정 존재 여부와 무관한 하나의 오류 문구로 표시한다 (`login/page.tsx:82`, `components/LoginForm.tsx:56-72`). |
| 데스크톱 로그인 화면 | 충족 | 지식 비주얼과 인증 패널을 grid 두 열로 나란히 제공하고 (`login/page.tsx:18-89`, `globals.css:176-183`), 인증 패널 안에 제품명·로그인 안내·Google CTA·가입 연결을 모두 둔다 (`login/page.tsx:59-87`). |
| 모바일 로그인 화면 | 충족 | 900px 이하에서 한 열로 전환하며 인증 패널이 `order: 1`로 먼저 나타난다. 패널과 주요 내용은 `min-width: 0` 및 모바일 여백 규칙으로 축소 가능하다 (`globals.css:395-415`, `609-618`, `663-685`). |
| OAuth 요청 진행 중 | 충족 | 제출 중 CTA를 비활성화하고, `aria-busy`, 버튼 레이블, live-region 진행 안내로 중복 시작을 막고 상태를 알린다 (`components/LoginForm.tsx:28-45`, `75-79`, `118-123`). |
| 가입 화면 연결 | 충족 | 로그인 안내 링크가 정확히 `/signup`을 가리킨다 (`login/page.tsx:85-87`). |

## 검증 증적

- `pnpm test -- tests/login-page-route.test.tsx tests/LoginForm.test.tsx tests/auth-callback-route.test.ts` (`apps/dashboard`에서 실행): 통과 — 64개 파일, 300개 테스트.

관련 Vite 설정 및 Node 경고는 있었으나 테스트 실패는 없었다. delta의 모든
Given/When/Then과 r1 수정 요구사항이 구현에서 충족되는 것을 확인했다.

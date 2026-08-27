# Spec Conformance Review — r1

## 판정

**needs_fix**

## 검토 범위

- delta: `specs/google-authentication/spec.md`의 `Google 단일 인증`
- 구현: `/login`, `LoginForm`, OAuth 콜백 및 로그인 전용 반응형 스타일

## 확인 결과

| delta 시나리오 | 결과 | 근거 |
| --- | --- | --- |
| 로그인 시작 | 충족 | `LoginForm`은 Google provider와 `/auth/callback?next=/` 내부 콜백으로 OAuth를 시작한다. |
| 인증 실패 | 충족 | 콜백은 실패 시 `/login?error=auth`로 이동하고, 폼은 단일 오류 문구만 표시한다. |
| 데스크톱 로그인 화면 | 부분 충족 | split 레이아웃과 지식 미리보기는 제공하지만, 인증 영역 자체에는 제품명이 없다. |
| 모바일 로그인 화면 | 충족 | 900px 이하에서 인증 패널이 먼저인 한 열이 되고, 640px 이하 여백도 조정한다. `min-width: 320px`와 `minmax(0, …)`로 가로 넘침을 방지한다. |
| OAuth 요청 진행 중 | 충족 | CTA가 비활성화되고 `aria-busy` 및 진행 안내를 표시한다. |
| 가입 화면 연결 | 충족 | 로그인 안내 링크가 `/signup`을 가리킨다. |

## 수정 필요 사항

1. **인증 영역의 제품명 부재**
   - delta 요구사항은 인증 영역이 제품명, 로그인 안내, Google CTA, 가입 화면 연결을 제공하도록 요구한다.
   - 현재 `apps/dashboard/app/(auth)/login/page.tsx:58-89`의 인증 영역에는 로그인 안내·CTA·가입 링크만 있다. `NexusWiki`는 좌측 시각 보조 영역에 있고, 인증 영역 안의 `login-mobile-brand`는 `aria-hidden="true"`이며 데스크톱에서는 `display: none`이다(`page.tsx:60-69`, `globals.css:626-628`).
   - 따라서 데스크톱 인증 패널은 시각 보조 영역과 독립적으로 제품명을 제공하지 못한다. 인증 패널에 접근 가능한 제품명을 상시 표시하고, 이를 확인하는 렌더링 테스트를 추가해야 한다.

## 검증 증적

- `pnpm test -- tests/login-page-route.test.tsx tests/LoginForm.test.tsx tests/auth-callback-route.test.ts` (`apps/dashboard`에서 실행): 통과 — 64개 파일, 300개 테스트.
- 관련 단위 테스트는 OAuth 시작·단일 오류·진행 중 중복 차단·가입 링크·콜백 목적지 정규화를 확인한다. 다만 인증 패널 내부의 제품명 요구사항은 검증하지 않아 위 불일치를 발견하지 못한다.

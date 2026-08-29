## Why

현재 `/login`은 Google OAuth 단일 인증만 제공하지만, 최소 중앙 정렬 화면이라
NexusWiki의 "원문과 위키를 함께 추적하는 지식 도구"라는 제품 맥락을 전달하지
못한다. 확정된 v3 로그인 템플릿을 프로덕션 화면에 적용해, 인증 진입점에서도
제품의 조용하고 정돈된 편집형 경험을 일관되게 제공한다.

## What Changes

- `/login`을 데스크톱의 지식 비주얼·인증 패널 split 레이아웃과 모바일의 로그인
  우선 단일 열 레이아웃으로 개편한다.
- Google OAuth 단일 CTA, 로딩 상태, 오류의 단일 안내, `/signup` 연결을 유지한다.
- 로그인 화면에서 쓰는 로고·지식 랜드스케이프 에셋을 Next.js 정적 경로로 제공한다.
- 기존 `LoginForm`의 OAuth 시작·콜백 목적지·오류 처리 계약을 프레젠테이션과
  분리해 `/signup`의 현재 동작을 변경하지 않는다.

## Capabilities

### New Capabilities

- 없음.

### Modified Capabilities

- `google-authentication`: 로그인 화면이 Google 단일 인증을 접근 가능하고 반응형인
  제품 진입점으로 제공하는 표시 계약을 보강한다.

## Impact

- `apps/dashboard/app/(auth)/login/page.tsx`
- `apps/dashboard/components/LoginForm.tsx` 및 로그인 전용 프레젠테이션 구성요소
- `apps/dashboard/app/globals.css` 또는 로그인 범위 스타일
- `apps/dashboard/public/`의 로그인 이미지·로고 에셋
- Google OAuth 호출, `/auth/callback`, Supabase 설정, `/signup`의 인증 동작은
  변경하지 않는다.

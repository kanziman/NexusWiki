# tenant-isolation-reviewer r2

## 판정

**pass**

## 검토 범위

- 아카이브된 `redesign-google-auth-login` change의 proposal·design·tasks·delta spec
- r1 이후 추가된 로그인 인증 패널의 제품명·마크 표시
- `/login`의 OAuth 시작 상태, 기존 `/auth/callback` 및 요청 경로의 특권 클라이언트 유입 여부

## 확인 결과

### 테넌트 격리와 403 매핑

r1 이후 변경은 인증 패널에 정적 제품명과 공개 마크를 표시하는
`apps/dashboard/app/(auth)/login/page.tsx:60-69`뿐이다. 이 표시는 워크스페이스 ID,
테넌트 데이터, API 요청 또는 서버 액션을 새로 만들거나 전달하지 않는다.

`LoginForm`은 계속 publishable-key 브라우저 클라이언트로 Google OAuth 시작만 수행한다
(`apps/dashboard/components/LoginForm.tsx:34-40`). `service_role`, `SERVICE_ROLE`,
`service_client`가 dashboard 사용자 요청 경로에 유입되지 않았고,
`scripts/ci_check_service_usage.sh`도 통과했다. 따라서 RLS 우회 경로나 영향 행 수 0을
성공으로 처리해야 하는 workspace-scoped mutation이 이 change로 추가되지 않았다.
403 매핑 대상과 worker의 명시적 `workspace_id` 범위·at-least-once 멱등 처리에도 변경이 없다.

### OAuth·보안과 멱등성

- CTA는 현재 origin의 `/auth/callback?next=/`만 OAuth redirect 대상으로 전달한다
  (`LoginForm.tsx:34-40`). 제품명 표시는 인증 요청의 입력값이나 목적지를 바꾸지 않는다.
- 콜백은 authorization code를 한 번만 교환하고(`apps/dashboard/app/auth/callback/route.ts:29-33`),
  스펙이 정한 `/` 시작 및 `//` 비시작 목적지 정규화 계약을 그대로 유지한다
  (`route.ts:6-8`, `openspec/specs/google-authentication/spec.md:49-55`).
- 제출 중 초기 가드와 비활성화 상태가 유지되어 같은 화면에서 OAuth 시작을 중복하지
  않는다(`LoginForm.tsx:28-32, 75-79`). 이 UI 변경은 1회용 authorization code 교환 경계나
  워커 작업의 멱등성에 영향을 주지 않는다.

### 오류 노출과 조용한 실패

콜백 교환 실패와 OAuth 시작 실패는 모두 계정 존재 여부·내부 오류 원인을 노출하지 않는
동일한 일반 오류 문구로 귀결된다(`route.ts:34-35`, `LoginForm.tsx:42-45, 56-72`).
정적 제품명·마크 및 `LoginKnowledgePreview`의 순환 문구는 테넌트 데이터, API 응답,
자격 증명을 읽거나 노출하지 않는다.

## 실행한 검증

- `pnpm --dir apps/dashboard test -- tests/LoginForm.test.tsx tests/login-page-route.test.tsx tests/auth-callback-route.test.ts tests/middleware-auth.test.ts`
  - 64개 테스트 파일, 300개 테스트 통과
- `bash scripts/ci_check_service_usage.sh`
  - 246개 파일 검사 통과; worker 밖 특권 service client 사용 없음
- 로그인 관련 변경 파일 대상 `git diff --check` 통과

## 잔여 지적 사항

없음. r1 이후의 제품명 표시 추가로 인한 테넌트 격리, 403 매핑, OAuth 보안, 멱등성 또는
조용한 실패 회귀를 발견하지 못했다.

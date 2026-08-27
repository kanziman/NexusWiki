# tenant-isolation-reviewer r1

## 판정

**pass**

## 검토 범위

- 아카이브된 `redesign-google-auth-login` change의 proposal·design·tasks·delta spec
- `/login` 프레젠테이션 변경과 `LoginForm`의 OAuth 시작 상태
- 기존 `/auth/callback`의 목적지 정규화·코드 교환·실패 처리
- 사용자 요청 경로의 특권 Supabase 클라이언트 유입 여부

## 확인 결과

### 테넌트 격리와 403 매핑

이 change는 로그인 프레젠테이션과 OAuth 시작 UI만 바꾸며, 워크스페이스 데이터의
조회·생성·수정·삭제 경로를 추가하거나 수정하지 않는다. 따라서 RLS를 우회할 수 있는
사용자 요청 경로도, 영향 행 수 0을 성공으로 오인할 수 있는 workspace-scoped mutation도
새로 만들지 않았다. `LoginForm`은 브라우저용 publishable-key 클라이언트로 Google OAuth
시작만 수행한다(`apps/dashboard/components/LoginForm.tsx:37`).

`scripts/ci_check_service_usage.sh`는 통과했고, dashboard 소스에 `service_role`,
`SERVICE_ROLE`, `service_client` 사용이 추가되지 않았음을 재확인했다. 이 change에는
특권 처리나 작업 핸들러가 없으므로 worker의 명시적 `workspace_id` 범위 및 at-least-once
멱등 upsert 계약에 영향을 주지 않는다.

### OAuth·보안 계약

- CTA는 기존과 동일하게 현재 origin의 `/auth/callback?next=/`만 redirect 대상으로
  전달한다(`LoginForm.tsx:34-40`).
- callback은 authorization code를 한 번만 교환하고(`route.ts:29-33`), `/`로 시작하면서
  `//`로 시작하지 않는 내부 경로만 허용한다(`route.ts:6-8`).
- 코드 교환 실패는 원인이나 계정 존재 여부를 노출하지 않고
  `/login?error=auth`로 이동한다(`route.ts:34-35`). 로그인 화면과 OAuth 시작 실패도
  동일한 일반 오류 문구만 표시한다(`LoginForm.tsx:42-45, 56-72`).
- 제출 중에는 버튼을 비활성화하고 초기 진입 가드도 유지해 동일 화면에서 OAuth 시작을
  중복 요청하지 않는다(`LoginForm.tsx:28-32, 75-79`). 이는 OAuth authorization code의
  1회 교환 경계와 충돌하지 않는다.

### 조용한 실패

추가된 지식 미리보기는 정적 문구와 브라우저 내 상태 순환만 수행하며
(`apps/dashboard/components/LoginKnowledgePreview.tsx:12-51`), 테넌트 데이터·API 응답·
자격 증명을 읽거나 노출하지 않는다. 공개 이미지도 dashboard의 정적 asset으로만 제공된다.

## 실행한 검증

- `pnpm --dir apps/dashboard test -- tests/LoginForm.test.tsx tests/login-page-route.test.tsx tests/auth-callback-route.test.ts tests/middleware-auth.test.ts`
  - 64개 테스트 파일, 300개 테스트 통과
- `bash scripts/ci_check_service_usage.sh`
  - 246개 파일 검사 통과; worker 밖 특권 service client 사용 없음
- 로그인 관련 변경 파일 대상 `git diff --check` 통과

## 잔여 지적 사항

없음. 이 review gate의 범위에서 수정이 필요한 테넌트 격리·403·OAuth 보안·멱등성·조용한 실패 회귀를 발견하지 못했다.

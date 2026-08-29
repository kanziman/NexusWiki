# tenant-isolation-reviewer r1

## 판정

**pass**

## 검토 범위

- 아카이브된 `restore-login-knowledge-preview-typing` change의 proposal·design·tasks·delta spec
- 로그인 모션 구현: `LoginKnowledgePreview`, `LoginHeroTitle`, `/login` 및 로그인 전용 CSS
- 기존 OAuth 시작·콜백 경로: `LoginForm`, `/auth/callback`
- 테넌트 격리, 403 매핑, OAuth 보안, 멱등성 및 조용한 실패 회귀

## 확인 결과

### 테넌트 격리와 403 매핑

이번 변경은 클라이언트에서 고정된 데모 문장과 표시 상태만 갱신한다.
`LoginKnowledgePreview`와 `LoginHeroTitle`은 워크스페이스 ID, 사용자 ID, 테넌트 데이터,
API·서버 액션을 읽거나 전달하지 않는다. `/login`도 두 컴포넌트를 화면에 배치할 뿐
요청 경로나 인증 권한을 바꾸지 않는다.

`service_role`, `service_client` 또는 기타 RLS 우회 자격 증명이 dashboard 사용자 요청
경로에 추가되지 않았으며, `ci_check_service_usage.sh`는 250개 파일 검사에서 통과했다.
workspace-scoped mutation이나 영향 행 수 0의 403 변환 경로를 신설·변경하지 않았으므로,
이 change에 기인한 403 매핑 또는 RLS 경계 회귀는 없다.

### OAuth 보안과 멱등성

- Google CTA는 기존대로 현재 origin의 `/auth/callback?next=/`만 `redirectTo`로 전달한다
  (`apps/dashboard/components/LoginForm.tsx:34-40`).
- 콜백은 authorization code가 있을 때만 `exchangeCodeForSession(code)`를 한 번 호출하고,
  실패 시 `/login?error=auth`로 보낸다
  (`apps/dashboard/app/auth/callback/route.ts:29-35`).
- `next`는 `/`로 시작하면서 `//`로 시작하지 않는 내부 경로만 통과시킨다
  (`apps/dashboard/app/auth/callback/route.ts:6-8`). 관련 회귀 테스트도 통과했다.
- CTA의 `submitting` 초기 가드와 `disabled` 상태가 유지되어 동일 화면에서 OAuth 시작을
  중복할 수 없다. 새 타이핑 타이머는 표시 전용이며 unmount·비가시 전환 시 timeout을
  정리하므로 인증 코드 교환이나 워커 작업의 멱등성 경계와 교차하지 않는다.

### 조용한 실패와 정보 노출

타이핑 시나리오는 소스명·위키명이 아닌 고정된 개수 표기만 보여 주며, `aria-hidden`으로
반복 데모 본문을 보조 기술에서 제외한다. 테넌트별 문서, 계정 존재 여부, 자격 증명,
내부 OAuth 오류를 노출하지 않는다. OAuth 시작 실패와 콜백 실패는 모두 기존의 단일
일반 오류 문구로 귀결되어 계정 열거 정보를 제공하지 않는다.

감소 모션 또는 비가시 탭 전환은 현재 시나리오를 완성된 정적 표시로 두고 타이머를
정리할 뿐 실패를 삼키거나 보안 상태를 바꾸지 않는다.

## 실행한 검증

- `pnpm --dir apps/dashboard test -- tests/LoginKnowledgePreview.test.tsx tests/login-page-route.test.tsx tests/auth-callback-route.test.ts`
  - 65개 테스트 파일, 305개 테스트 통과
- `bash scripts/ci_check_service_usage.sh`
  - 250개 파일 검사 통과; 사용자 요청 경로의 특권 service client 유입 없음
- 로그인 관련 변경 파일 대상 `git diff --check` 통과

## 잔여 지적 사항

없음.

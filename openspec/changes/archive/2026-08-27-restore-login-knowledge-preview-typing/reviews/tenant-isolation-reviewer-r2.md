# tenant-isolation-reviewer r2

## 판정

**pass**

## 재검토 범위

- 아카이브된 `restore-login-knowledge-preview-typing` change의 proposal·design·tasks·delta spec
- r1 `pass` 이후 조정된 헤드라인 감소 모션 처리: `LoginHeroTitle`과 로그인 전용 CSS·테스트
- 로그인 모션 구현 및 기존 OAuth 시작·콜백 경로의 테넌트 격리·403 매핑·조용한 실패 회귀

## 확인 결과

### 테넌트 격리와 403 매핑

`LoginHeroTitle`은 `document.visibilityState`와 `prefers-reduced-motion`만 읽어 밑줄의
표시 클래스를 선택한다. 워크스페이스·사용자 식별자, 테넌트 데이터, API·서버 액션을
읽거나 전달하지 않는다. `LoginKnowledgePreview`도 고정 데모 문장과 로컬 표시 상태만
사용한다.

이번 r2 조정은 감소 모션 또는 비가시 상태에서 `is-complete` 클래스를 선택해 완성된 밑줄을
그리는 것으로 한정된다. 사용자 요청 경로, RLS 정책, workspace-scoped mutation, 영향 행 수
0의 403 변환 경로에는 변경이 없으므로 테넌트 경계와 403 매핑 회귀가 없다.

### 특권 접근·OAuth·멱등성

- `service_role`, `service_client` 및 브라우저 노출 가능한 특권 자격 증명은 로그인 모션
  변경에 추가되지 않았다. `ci_check_service_usage.sh`가 252개 파일을 검사해 통과했다.
- Google OAuth 시작은 기존의 내부 `/auth/callback?next=/` redirect 대상과 CTA의
  `submitting` 중복 방지 상태를 유지한다.
- 콜백은 authorization code가 있을 때 한 번만 교환하고, 실패 시 기존 단일
  `/login?error=auth` 경로로 이동한다. 새 헤드라인 상태는 인증 코드 교환·세션·워커 작업과
  교차하지 않는다.

### 조용한 실패와 정보 노출

헤드라인의 모션 완료 여부는 로컬 접근성/탭 상태만 반영하며 계정 존재 여부, 워크스페이스
데이터, OAuth 상세 오류를 노출하지 않는다. 미리보기의 내용도 고정 데모이며 반복 본문은
`aria-hidden`으로 제외되어, 테넌트별 데이터가 사용자에게 노출될 경로가 없다.

## 실행한 검증

- `pnpm --dir apps/dashboard test -- tests/LoginKnowledgePreview.test.tsx tests/LoginHeroTitle.test.tsx tests/login-page-route.test.tsx tests/auth-callback-route.test.ts`
  - 66개 테스트 파일, 306개 테스트 통과
- `bash scripts/ci_check_service_usage.sh`
  - 252개 파일 검사 통과; 사용자 요청 경로의 특권 service client 유입 없음
- 로그인 모션 관련 변경 파일 대상 `git diff --check` 통과

## 잔여 지적 사항

없음.

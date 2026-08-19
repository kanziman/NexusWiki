## 1. 전용 생성 라우트

- [x] 1.1 `/w/new` 라우트를 신설해 소속 개수와 무관하게 도달 가능하게 한다.
  - Given: 인증 사용자가 소속 워크스페이스를 1개 이상 갖고 있다.
  - When: 사용자가 `/w/new`에 접근한다.
  - Then: `/`의 자동 리다이렉트 분기를 거치지 않고 워크스페이스 이름 입력 폼이 렌더링된다.
  - Verification: `pnpm typecheck`, `pnpm lint`, `pnpm test -- --run`(`tests/new-workspace-route.test.tsx`), `pnpm build` 전부 통과.

## 2. 상한 이내 생성과 서버 측 정본 판정

- [x] 2.1 `createPersonalWorkspace`에 소속 3개 상한 검사를 추가한다.
  - Given: 요청자의 RLS 스코프 소속 워크스페이스 개수가 3개 이상이다.
  - When: 사용자가 `/w/new`에서 이름을 제출한다.
  - Then: 서버 액션이 INSERT 없이 상한 오류를 반환하고, 3개 미만이면 기존 온보딩 흐름(전역 slug 충돌 재시도 포함)대로 생성에 성공한다.
  - Verification: `pnpm test -- --run`(`tests/onboarding-actions.test.ts`의 상한 케이스), `pnpm typecheck`, `pnpm lint` 통과.

## 3. 워크스페이스 스위처 진입점

- [x] 3.1 "새 워크스페이스 생성" 링크를 `/w/new`로 연결하고 상한 도달 시 숨긴다.
  - Given: 워크스페이스 스위처가 소속 목록을 갖고 있다.
  - When: 소속이 3개 미만이면 링크가 `/w/new`를 가리키며 렌더링되고, 3개 이상이면 렌더링되지 않는다.
  - Then: 상한에 도달한 사용자는 눌러도 실패하는 죽은 링크를 보지 않는다.
  - Verification: `pnpm test -- --run`(`tests/WorkspaceSwitcher.test.tsx`의 두 케이스), `pnpm typecheck`, `pnpm lint` 통과.

## 4. 사후 문서화 검증

- [x] 4.1 전체 검증 스위트를 다시 실행해 세 태스크의 변경이 서로 충돌하지 않음을 확인한다.
  - Given: 1~3의 구현이 모두 커밋되어 있다(브랜치 `fix/checklist-verification-and-auth-bugs`, PR #43).
  - When: `pnpm typecheck`, `pnpm lint`, `pnpm test -- --run`, `pnpm build`를 순서대로 실행한다.
  - Then: 45개 테스트 파일 193개 테스트 전부 통과, 타입·린트 오류 없음, 프로덕션 빌드 성공(`/w/new` 라우트가 정적 세그먼트로 별도 생성됨을 빌드 출력에서 확인).
  - Verification: 위 네 명령 전부 통과 — 이 세션에서 실측했다.

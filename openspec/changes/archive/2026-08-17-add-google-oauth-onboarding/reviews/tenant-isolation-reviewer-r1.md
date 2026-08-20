# Tenant Isolation 리뷰 — add-google-oauth-onboarding r1

- 판정: **pass**
- 대상: `git diff main...fix/checklist-verification-and-auth-bugs` (PR #43, 커밋 `a26b0cc97e29881ef96bef2d663b884b2cec1723`)
- 일시: 2026-08-20T00:00:00+09:00
- 참고: 이 PR은 이미 프로덕션에 배포된 뒤 뒤늦게 올라온 사후 리뷰다. `/opsx:apply` 표준 흐름이 아니므로 change 경로(`add-google-oauth-onboarding`)에 이 브랜치의 proposal/tasks가 없을 수 있다 — 격리 관점만 판정한다.

## 검사 결과

| # | 항목 | 결과 | 근거 |
| --- | --- | --- | --- |
| A-1 | 사용자 경로의 service_role | 통과 | diff 전체에 `service_role`/`service_client`/`SUPABASE_SERVICE*` 문자열 없음(`grep` 확인). `onboarding-actions.ts`, `app/w/new/page.tsx`, `app/page.tsx` 모두 `lib/supabase/server.ts`의 `createClient()`를 쓰며, 이는 요청자 쿠키(JWT)로 만든 `user_client`다(`apps/dashboard/lib/supabase/server.ts:14-16` 주석: "요청자 자신의 세션 쿠키로 클라이언트를 만든다"). |
| A-2 | 신규 테이블 RLS 동시 활성화 | 해당 없음 | 이 diff에 마이그레이션 파일이 없다 (`git diff --stat`에 `supabase/migrations/` 없음). |
| A-3 | anon 신규 GRANT/정책 | 해당 없음 | SQL 변경 없음. |
| A-4 | 워커 workspace_id 명시 필터 | 해당 없음 | 워커/service_role 코드 변경 없음. |
| A-5 | 신규 자식 테이블 복합 FK | 해당 없음 | 신규 테이블 없음. |
| B-6 | 0행 → 403 매핑 | 해당 없음 | 이 diff는 `apps/api`(FastAPI 403 매핑 계층)를 건드리지 않는다. `apps/dashboard`의 Server Action은 HTTP status가 아니라 `{ error }` 문자열을 반환하는 UI 계층이며, `USING`에 막힌 UPDATE/DELETE 경로도 없다(모두 INSERT/SELECT). |
| B-7 | 42501 → 403 매핑 | 해당 없음 | 같은 이유. `createPersonalWorkspace`의 INSERT는 `owner_id = auth.uid()`로 항상 채워 넣으므로 `WITH CHECK` 위반 자체가 구조적으로 발생하지 않는다(`apps/dashboard/app/onboarding-actions.ts:48`). |
| C-8 | 멱등 upsert 키 | 해당 없음 | job 핸들러 변경 없음. `workspaceSlug` 재시도 루프(23505 충돌 시 숫자 접미사)는 기존 로직 그대로이며 이번 diff가 건드리지 않았다. |
| C-9 | `jobs` 직접 UPDATE 금지 | 해당 없음 | `jobs` 테이블 관련 코드 변경 없음. |
| D-10~14 | 벡터 검색 / 토크나이저 / 프롬프트 / 인용 앵커 | 해당 없음 | 검색·LLM·프롬프트 경로 변경 없음. 이번 diff는 대시보드 인증/온보딩 UI와 CSS 정리뿐이다. |
| E-15 | 마이그레이션 번호 순서 | 해당 없음 | 신규 마이그레이션 없음. |

## 요청받은 4가지 항목에 대한 상세 판단

### 1. `middleware.ts` — matcher에 `/` 추가

- 변경 내용: `apps/dashboard/middleware.ts:59,75`. 조건이 `pathname.startsWith("/w/") && !user`에서 `(pathname.startsWith("/w/") || pathname === "/") && !user`로, matcher가 `["/w/:path*", "/login"]`에서 `["/w/:path*", "/login", "/"]`로 확장됐다.
- **matcher 과잉/과소매칭 없음.** `"/"`는 Next.js matcher에서 정확히 루트 경로 하나만 매칭하는 리터럴이다(`:path*` 같은 캡처 세그먼트가 없음) — `/w/:path*`가 이미 담당하던 워크스페이스 하위 트리와 겹치지 않고, `/api/*`·`/_next/*`·정적 자산 등 다른 경로를 새로 끌어들이지도 않는다.
- **이 변경은 게이트를 좁힌 게 아니라 넓혔다.** 기존에는 `/`가 matcher 밖이라 미들웨어를 아예 거치지 않고 `app/page.tsx`가 렌더링됐고, 미인증 사용자는 `WorkspaceOnboarding` 폼을 보되 제출 시에만 서버 액션 내부의 `if (!user) return { error: "로그인이 필요합니다." }`(`app/onboarding-actions.ts:39`)로 막혔다. 이번 변경 후에는 미인증 사용자가 `/`에 도달하기 전에 `/login`으로 리다이렉트된다 — 노출 표면이 줄었을 뿐 새로 열린 경로는 없다.
- **CVE-2025-29927 관련**: `package.json`에서 Next.js `15.5.22` 확인(`apps/dashboard/package.json:25`) — 불변 규칙의 `>= 15.2.3`을 만족하며 이 PR이 버전을 낮추지도 않았다. `x-middleware-subrequest` 우회는 이 diff와 무관.
- **리다이렉트 루프 없음**: `/login` 조건(`user` 존재 시 `/`로)과 `/` 조건(`!user` 시 `/login`으로)이 상호 배타적이라 핑퐁이 발생하지 않는다.
- **`app/page.tsx`의 주석·로직도 일치하게 갱신됐다** (`apps/dashboard/app/page.tsx:11-16`) — "middleware.ts가 `/`를 게이트하지 않으므로"에서 "matcher가 `/`를 포함하므로 미인증 요청은 도달 전에 리다이렉트된다"로 정정. 로그인 판정을 두 곳에서 하지 않는다는 D-02 경계도 유지된다.
- **판정: 통과.** 우회도, 과매칭도, 이중 판정 중복도 없다.

### 2. `app/onboarding-actions.ts` — 워크스페이스 3개 상한, 레이스 컨디션

- `apps/dashboard/app/onboarding-actions.ts:39,48-53`: `getUser()`로 미인증을 먼저 걸러낸 **뒤에** `supabase.from("workspaces").select("id")`로 개수를 세고, 3개 이상이면 생성을 거부한다. 필터 없는 조회는 RLS `workspaces_select_member`(`owner_id = auth.uid() or is_workspace_member(id)`)가 요청자 소속으로만 좁혀주므로, 이 조회는 항상 **요청자 자신의** 워크스페이스 개수만 센다. 다른 테넌트의 개수를 세거나 다른 테넌트에 영향을 주는 경로가 아니다.
- **레이스 컨디션은 실재한다**: 동시에 두 요청이 들어오면 둘 다 "개수 2"를 읽고 통과해 상한을 3→4로 넘길 수 있다. DB 쪽에 이를 막는 유일 제약(예: `check` 또는 partial unique index)이 없으므로 애플리케이션 레이어의 TOCTOU다.
- **그러나 이것은 테넌트 경계를 넘지 않는다.** 상한이 보호하는 것은 "요청자 자신의 리소스 생성 개수"이지 다른 테넌트의 데이터나 접근 권한이 아니다. RLS 정책·권한 매트릭스·격리 술어는 전혀 우회되지 않으며, 최악의 결과는 한 사용자가 자기 소유 워크스페이스를 3개가 아니라 4~5개 만드는 정도다(남용 방지 가드레일의 완화이지 보안 사고가 아니다). CLAUDE.md가 `blocked` 기본 대상으로 지정한 A-1/A-3/A-4(사용자 경로 service_role, anon GRANT, 워커 필터 누락) 중 어디에도 해당하지 않는다.
- **판정: 허용 가능한 UX 가드레일 수준.** 정확한 상한 집행이 필요하다면 후속 개선(예: `workspaces` 테이블에 소유자별 개수 제약을 거는 DB 트리거, 혹은 advisory lock)을 권고하되, 이번 리뷰의 pass/blocked 판정에는 영향을 주지 않는다.

### 3. `app/w/new/page.tsx` — 별도 정적 세그먼트, 인증 게이트 가정

- `git ls-tree`로 확인한 트리 구조: `apps/dashboard/app/w/new/page.tsx`는 `apps/dashboard/app/w/[workspaceId]/`와 **형제 디렉터리**다. Next.js App Router는 정적 세그먼트를 동적 세그먼트보다 우선 매칭하므로 `/w/new`는 항상 이 정적 라우트로 해석되고, `workspaceId="new"`로 동적 라우트 레이아웃(`[workspaceId]/layout.tsx`)에 걸리지 않는다 — 라우트 충돌 없음.
- 인증 게이트 가정 확인: `middleware.ts`의 matcher `"/w/:path*"`는 `path-to-regexp`의 `zero-or-more` 세그먼트 캡처라 `/w/new`도 `/w/`로 시작하는 경로로서 매칭된다. 실제로 `apps/dashboard/tests/middleware-auth.test.ts`가 `/w/workspace-1/sources`에 대해 동일 패턴의 리다이렉트를 검증하고 있어 매칭 동작이 검증됐다(단, `/w/new` 자체를 겨냥한 미들웨어 테스트 케이스는 없음 — 커버리지 공백이지 결함은 아니다).
- **심층 방어도 확인됨**: 설령 미들웨어가 어떤 이유로든 건너뛰이더라도, `app/w/new/page.tsx`의 `supabase.from("workspaces").select("id")`는 `to authenticated` 정책만 있는 `workspaces` 테이블을 anon 역할로 조회하면 0행이 돌아오고(`anon`은 정책 자체가 없어 완전 거부, CLAUDE.md 「역할은 셋」), 실제 생성 시도는 `createPersonalWorkspace` 내부의 `getUser()` 체크가 재차 막는다. 페이지 자체에 별도 `getUser()` 게이트가 없다는 점이 유일한 아쉬움이지만, 이는 미들웨어가 이미 걸러내는 것을 전제로 한 기존 패턴(`app/page.tsx`, `[workspaceId]/layout.tsx`)과 동일한 설계다.
- **판정: 가정이 맞다.** 별도 인증 처리가 필요하다는 근거를 찾지 못했다.

### 4. `components/WorkspaceSwitcher.tsx` — 표시용 조건과 서버 재검증의 이원화

- `apps/dashboard/components/WorkspaceSwitcher.tsx:123`: `workspaces.length < 3`일 때만 "새 워크스페이스 생성" 링크(`/w/new`)를 보여준다. 이 컴포넌트는 `"use client"` 컴포넌트이고 `workspaces` prop은 `[workspaceId]/layout.tsx`가 RLS로 조회한 목록을 그대로 받는다 — 서버가 이미 계산한 값을 표시만 할 뿐 자체적으로 권한을 판정하지 않는다.
- 실제 상한 집행은 `createPersonalWorkspace`(`onboarding-actions.ts:48-53`)가 **다시** `select("id")`로 세어 판정한다 — 표시값과 무관하게 독립적으로 재검증한다. 두 곳이 같은 RLS 스코프(`workspaces_select_member`)를 쓰므로 정상 상황에서는 일치하고, 레이스가 나더라도(2번 항목) 서버 액션이 최종 정본이라 클라이언트 표시가 상한을 우회하는 경로가 되지 않는다 — 링크를 억지로 다시 보이게 만들어(devtools 등으로) `/w/new`에 진입해도 서버 측 재검증이 막는다.
- **판정: 이원화가 올바르게 됐다.** 클라이언트는 UX 힌트, 서버 액션이 유일한 권위. 3번 항목의 `app/w/new/page.tsx` 자체도 진입 시점에 한 번 더 개수를 세어 폼 노출 여부를 판정하므로 3중 확인(스위처 표시 → 페이지 진입 판정 → 서버 액션 최종 판정)이며, 마지막 것만 실제 쓰기를 좌우한다.

## 조치가 필요한 항목

없음. (참고용 개선 제안 1건 — 차단 사유 아님)

1. **워크스페이스 3개 상한의 TOCTOU** (심각도: 낮음, 참고용)
   - 위치: `apps/dashboard/app/onboarding-actions.ts:48-53`
   - 깨지는 것: 동시 제출 시 상한을 1~2개 초과할 수 있다. 단, 이는 요청자 자신의 리소스 개수 제한이며 테넌트 경계·RLS·권한 매트릭스와 무관하다.
   - 조치(선택): DB 레벨 제약(예: `owner_id`별 개수를 세는 `check` 트리거)이나 advisory lock으로 원자성을 확보할 수 있으나, 현재 리스크 수준에서는 필수 아님.

## 판정 근거

이 PR은 `apps/dashboard`(Next.js) 계층의 인증/온보딩 UI 수정과 CSS 정리로 한정되며, `supabase/migrations/`·`apps/api`(서비스 역할·워커·403 매핑 계층)·검색/LLM 파이프라인을 전혀 건드리지 않는다. 모든 신규/변경 코드가 요청자 쿠키 기반 `user_client`만 사용하고, RLS 정책(`workspaces_select_member`, `workspaces_insert_self_owned`)의 스코프를 그대로 신뢰하며 우회하지 않는다. `middleware.ts` 변경은 게이트를 좁힌 것이 아니라 이전에 뚫려 있던(비록 서버 액션이 2차로 막고 있었지만) `/` 경로의 인증 확인을 미들웨어 단으로 앞당겨 강화한 것이다. 3개 상한의 레이스 컨디션은 실재하는 결함이지만 테넌트 경계를 넘지 않는 자기 자신 리소스에 대한 소프트 가드레일이라 `needs_fix`/`blocked` 기준(CLAUDE.md의 A-1/A-3/A-4 및 테넌트 경계 침해)에 해당하지 않는다. 이상으로 `pass`.

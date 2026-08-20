# Spec Conformance 리뷰 — add-google-oauth-onboarding r1

- 판정: **blocked**
- 대상: `git diff main...fix/checklist-verification-and-auth-bugs` (base `ddf1d71f49f57a1a2cf1f8987005d2271e7d4765`, head `a26b0cc97e29881ef96bef2d663b884b2cec1723`, GitHub PR #43)
- 일시: 2026-08-20T08:31:00+09:00

## 사전 정황

이 PR은 정식 `/opsx:propose`~`/opsx:apply` 리뷰 게이트를 거치지 않고 로컬 main에 직접 7개 커밋으로 만들어진 뒤, 사후에 동일 커밋들을 가리키는 브랜치로 재구성되어 PR #43으로 올라갔다(reflog 확인: `main`이 이 커밋들을 포함한 채로 존재하다가 `origin/main`으로 reset되고 `fix/checklist-verification-and-auth-bugs`가 같은 tip을 유지). `openspec/changes/add-google-oauth-onboarding/reviews/`에는 이번 리뷰 이전에 아무 파일도 없었다 — 즉 이 change에 대한 spec-conformance 리뷰가 이번이 처음이다.

diff 중 CLEAN-01~04 색 토큰 정리, `CategoryLensFilter` 고아 컴포넌트 삭제, 로그인/가입 화면 로고 이미지 적용, 4화면 `.content` 패딩 통일은 이 change의 스펙 범위와 무관하다 — 판정에서 제외했다(사용자 지시 3항).

브랜치 `fix/checklist-verification-and-auth-bugs` 기준으로 `pnpm test -- --run`(46 files / 193 tests 전부 통과), `pnpm typecheck`, `pnpm lint` 를 직접 재실행해 확인했다(2026-08-20).

## 시나리오 판정

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| google-authentication / 로그인 시작 | 충족 (이번 PR 변경 없음) | `apps/dashboard/components/LoginForm.tsx:18-30` — `signInWithOAuth({ provider: "google", redirectTo: .../auth/callback?next=/ })` |
| google-authentication / 인증 실패 | 충족 (이번 PR 변경 없음) | `apps/dashboard/app/auth/callback/route.ts:31-34` — 실패 시 `destination = "/login?error=auth"`; 테스트 `apps/dashboard/tests/auth-callback-route.test.ts` |
| OAuth 콜백은 안전한 내부 경로만 따른다 / 외부 리다이렉트 거부 | 충족 (이번 PR 변경 없음) | `apps/dashboard/app/auth/callback/route.ts:6-8` `normalizeNext` — `/`로 시작하고 `//`가 아닌 경우만 통과 |
| workspace-entry-flow / One accessible workspace | 충족 (이번 PR 변경 없음) | `apps/dashboard/app/page.tsx` — `workspaces.length === 1` → `redirect(workspacePath(...))` (PR에서는 주석만 갱신, 로직 불변) |
| workspace-entry-flow / No accessible workspaces | 충족 — **단, 이 PR이 처음으로 실제 충족시켰다** | `apps/dashboard/middleware.ts:59,75` — matcher에 `"/"` 추가 + `pathname === "/"` 조건. PR 이전에는 미인증 방문자도 루트에서 온보딩 폼을 그대로 렌더링했다(아래 「판정 근거」 참조). 테스트 `apps/dashboard/tests/middleware-auth.test.ts` |
| workspace-onboarding / 첫 워크스페이스 생성 | 충족 | `apps/dashboard/app/onboarding-actions.ts:32-74` `createPersonalWorkspace`, `apps/dashboard/components/WorkspaceOnboarding.tsx`; 테스트 `apps/dashboard/tests/onboarding-actions.test.ts:31-46` "personal workspace를 요청자 owner로 생성한다" |
| workspace-onboarding / 중복 이름 | 충족 | `apps/dashboard/app/onboarding-actions.ts:12-28,56-71` 숫자 접미사 재시도 루프; 테스트 `onboarding-actions.test.ts:48-59` |

델타 spec에 명시된 7개 시나리오 자체는 모두 충족한다. 문제는 그 위에 스펙에 없는 새 동작이 추가된 것이다.

## 조치가 필요한 항목

1. **셀프서브 워크스페이스 3개 상한이 스펙 어디에도 없다** — `apps/dashboard/app/onboarding-actions.ts:7-10,49-54`에 `MAX_PERSONAL_WORKSPACES = 3`이 도입됐고, 코드 자체 주석이 "auth-google-prd.md §5 에는 없는 값"이라고 명시한다. `openspec/changes/add-google-oauth-onboarding/specs/workspace-onboarding/spec.md`, `proposal.md`, `design.md` 어디에도 개수 상한이나 "이미 워크스페이스가 있는 사용자의 추가 생성" 관련 Requirement가 없다. Non-Goals(`design.md`)에도 언급이 없다. 근거 Scenario: workspace-onboarding의 두 Scenario는 모두 "RLS로 보이는 워크스페이스가 없는 인증 사용자"를 전제하며, `proposal.md:5`는 "온보딩은... 워크스페이스가 없을 때 첫 개인 워크스페이스를 만드는 흐름"이라고 명시적으로 범위를 0개 사용자로 좁혀 정의한다. 3개 상한은 그 범위 밖의 새 비즈니스 규칙이다. 제안: 이 change의 delta spec(`workspace-onboarding/spec.md`)에 상한 값과 근거를 Requirement/Scenario로 명문화하거나, 별도 change로 분리해 스펙을 갱신한다. 이미 `checklists_v2.json`에 사용자 결정 기록(`resolution` 필드, 2026-08-20)은 있지만 이는 OpenSpec 산출물이 아니라 v2 UI 체크리스트이며 이 change의 정본 스펙에 반영되지 않았다.

2. **`/w/new` 라우트는 workspace-onboarding 스펙 범위 밖의 새 사용자 흐름이다** — `apps/dashboard/app/w/new/page.tsx`(신설)는 "소속 워크스페이스가 이미 1~2개 있는 사용자"에게 `WorkspaceOnboarding` 폼을 재노출한다. 이는 workspace-onboarding capability의 Purpose("워크스페이스가 없는 인증 사용자가...")와 `proposal.md`의 온보딩 정의를 벗어난, "기존 사용자의 추가 워크스페이스 셀프서브 생성"이라는 새 사용자 관찰 가능 동작이다. `workspace-entry-flow` delta spec도 이 라우트나 "여러 워크스페이스 보유자의 추가 생성" 흐름을 다루지 않는다. `WorkspaceSwitcher.tsx:123-133`의 "새 워크스페이스 생성" 링크 대상 변경(`/` → `/w/new`)과 3개 이상일 때 링크 숨김도 같은 이유로 스펙 밖이다. 제안: 이 흐름을 정식 capability(예: `workspace-entry-flow` 또는 신규 capability)의 Requirement/Scenario로 명문화하는 change를 별도로 진행한다.

두 항목 모두 기존 델타 spec의 Scenario와 상충하거나 그것을 깨뜨리지는 않는다(순수 추가). 다만 코드를 고쳐서 해결할 문제가 아니라 — 구현은 테스트(`WorkspaceSwitcher.test.tsx`, `new-workspace-route.test.tsx`, `onboarding-actions.test.ts`)로 잘 검증되어 있다 — **스펙 문서 쪽의 사후 갱신 여부를 사람이 결정해야 하는 사안**이라 `blocked`로 분류했다.

## 판정 근거

델타 spec의 7개 Scenario는 코드·테스트로 모두 확인된다. 그러나 이번 PR은 그 범위를 벗어난 두 가지 사용자 관찰 가능 동작(워크스페이스 3개 상한, 기존 사용자를 위한 `/w/new` 추가 생성 라우트)을 스펙 갱신 없이 도입했다. 코드 자체 주석이 "PRD에 없는 값"이라고 자백하고 있고, `checklists_v2.json`의 `resolution` 기록은 OpenSpec 산출물이 아니므로 이 change의 정본 스펙과 여전히 어긋난 상태다. `/opsx:apply`가 금지하는 "스펙 밖 동작"에 해당하며, 해결에는 코드가 아니라 스펙 문서(및 그에 대한 사람의 결정)가 필요하므로 `needs_fix`가 아니라 `blocked`로 판정한다.

부수적으로, tasks.md의 1.x·2.x가 `- [x]`로 완료 처리된 원래 구현에는 middleware matcher가 `/`를 포함하지 않아 미인증 방문자가 루트에서 `WorkspaceOnboarding` 폼을 그대로 볼 수 있는 결함이 있었다(`checklists_v2.json`의 AUTH-06 재검증 기록, 2026-08-20). 이는 workspace-entry-flow/workspace-onboarding 두 capability가 전제하는 "인증 사용자"라는 조건이 실제로는 middleware로 강제되지 않았다는 뜻이며, 이 change에 대한 spec-conformance 리뷰가 `/opsx:apply` 당시 한 번도 수행되지 않았다는 정황(리뷰 디렉터리가 비어 있었음)과 일치한다. 이번 PR의 미들웨어 수정 자체(`middleware.ts:59,75`)는 스펙을 정확히 충족시키는 방향의 수정이라 이 항목은 조치 목록에 넣지 않았다 — 다만 원래의 "완료" 체크가 검증 없이 이루어졌다는 사실은 기록해 둔다.

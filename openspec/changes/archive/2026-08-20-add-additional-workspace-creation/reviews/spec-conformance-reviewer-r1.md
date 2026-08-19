# Spec Conformance 리뷰 — add-additional-workspace-creation r1

- 판정: **pass**
- 대상: `git diff main...fix/checklist-verification-and-auth-bugs` (head `821b12b43d2a23b7e1a031302d259b25ce3e350b`, GitHub PR #43) — 이번 라운드가 검토하는 것은 그 위에 추가된 순수 문서 커밋 `821b12b`(코드 변경 없음)이 기존 구현과 정합하는지다
- 일시: 2026-08-20T09:00:00+09:00

## 사전 정황

1라운드(`openspec/changes/add-google-oauth-onboarding/reviews/spec-conformance-reviewer-r1.md`)는 `/w/new` 라우트와 워크스페이스 3개 상한이 `add-google-oauth-onboarding`의 `workspace-onboarding` capability(0개 사용자 범위) 밖에서 스펙 갱신 없이 구현됐다는 이유로 `blocked` 판정했다. 커밋 `821b12b`는 코드를 전혀 건드리지 않고(`git show --stat 821b12b` — `openspec/changes/add-additional-workspace-creation/` 아래 4개 신규 파일만 추가) 그 두 동작을 새 capability `additional-workspace-creation`으로 사후 문서화했다.

`openspec validate add-additional-workspace-creation --strict` → `Change 'add-additional-workspace-creation' is valid` 확인. `pnpm test -- --run`(apps/dashboard) 재실행 → 46 files / 193 tests 전부 통과(이 세션에서 실측, 1라운드 수치와 일치).

## 시나리오 판정

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| 소속 개수와 무관한 전용 생성 라우트 / 소속이 있는 사용자가 전용 라우트에 진입 | 충족 | `apps/dashboard/app/w/new/page.tsx:13-34` — `workspaces.length >= 3` 미만이면 `WorkspaceOnboarding` 폼 렌더링, `/`의 리다이렉트 분기를 거치지 않는 독립 라우트. `apps/dashboard/app/page.tsx`(root)는 이 커밋에서도, 원 구현에서도 리다이렉트 로직이 불변(`git diff main...fix/checklist-verification-and-auth-bugs -- apps/dashboard/app/page.tsx` — 주석만 변경). 테스트 `apps/dashboard/tests/new-workspace-route.test.tsx:24-32`(소속 1개 → 폼 렌더링 확인) |
| 상한 이내 추가 워크스페이스 생성 / 상한 미만에서 생성 성공 | 충족 | `apps/dashboard/app/onboarding-actions.ts:32-74` `createPersonalWorkspace` — line 49에서 `supabase.from("workspaces").select("id")`로 RLS 스코프 소속 개수를 요청 시점에 재조회(클라이언트 표시 상태에 의존하지 않음, spec의 MUST NOT 충족). 테스트 `apps/dashboard/tests/onboarding-actions.test.ts:41-55` |
| 상한 이내 추가 워크스페이스 생성 / 상한 도달 시 생성 거부 | 충족 | `onboarding-actions.ts:50-54` `existing.length >= MAX_PERSONAL_WORKSPACES` → INSERT 없이 오류 반환. 테스트 `onboarding-actions.test.ts:82-89` "이미 3개 소속이면 생성하지 않고 상한 오류를 반환한다" |
| 상한 도달 시 죽은 링크를 만들지 않는다 / 상한 도달 시 진입점 숨김 | 충족 | `apps/dashboard/components/WorkspaceSwitcher.tsx:123` `workspaces.length < 3` 조건으로 링크 자체를 렌더링 트리에서 제외. 테스트 `apps/dashboard/tests/WorkspaceSwitcher.test.tsx:99-117` |
| 상한 도달 시 죽은 링크를 만들지 않는다 / 상한 미만에서 진입점 노출 | 충족 | `WorkspaceSwitcher.tsx:123-133` — `href="/w/new"`. 테스트 `WorkspaceSwitcher.test.tsx:85-97` |

5개 Scenario 전부 코드·테스트 증거로 확인됐다. `tasks.md`의 4개 task(1.1, 2.1, 3.1, 4.1)는 각각 위 Scenario들과 1:1로 대응하며 `- [x]` 처리가 정확하다 — task 4.1이 주장하는 "45개 테스트 파일 193개 테스트 전부 통과"는 이번 재실행에서도 동일하게 재현됐다(46 files로 표기 차이는 이번 실행 시 vitest 카운트 방식 문제가 아니라 실제로도 46 files임 — task 문서의 "45"는 근소한 오기이나 테스트 개수 193은 일치하며 판정에 영향 없음).

## 1라운드 지적 항목 정합 확인

1. **3개 상한** — 1라운드는 `openspec/changes/add-google-oauth-onboarding/specs/workspace-onboarding/spec.md`, `proposal.md`, `design.md` 어디에도 상한 Requirement가 없다고 지적했다. 이제 `openspec/changes/add-additional-workspace-creation/specs/additional-workspace-creation/spec.md:15-25`에 "상한 이내 추가 워크스페이스 생성" Requirement와 두 Scenario로 명문화됐고, 구현(`onboarding-actions.ts`)과 정확히 일치한다. **정합됨.**
2. **`/w/new` 라우트** — 1라운드는 이 라우트가 `workspace-onboarding` capability(Purpose: "워크스페이스가 없는 인증 사용자")를 벗어난 스펙 밖 동작이라고 지적했다. 이제 `spec.md:7-13`에 별도 Requirement로 명문화됐고, `design.md`가 라우트 설계 결정(정적 세그먼트 우선 매칭, 미들웨어 재게이트 안 함, 서버 액션 정본 판정)을 근거와 함께 기록한다. **정합됨.**

두 항목 모두 "코드를 스펙에 맞게 고침"이 아니라 "이미 스펙과 일치하는 코드에 맞춰 스펙을 사후 작성"하는 방향이었고, 문서와 코드를 대조한 결과 문구 차이 없이 일치한다.

## 경계 확인 — `add-google-oauth-onboarding`과의 관계

- `proposal.md:3`가 명시적으로 경계를 긋는다: `workspace-onboarding`은 "RLS로 보이는 워크스페이스가 0개일 때"로 범위가 좁혀져 있고, 이 change는 "이미 멤버인 사용자"를 대상으로 한다.
- `openspec/changes/add-google-oauth-onboarding/specs/workspace-onboarding/spec.md:3`의 Purpose("워크스페이스가 없는 인증 사용자가...")와 대조해도 모순이 없다 — 두 capability가 다루는 사용자 상태가 겹치지 않는다.
- `Modified Capabilities: (없음)`(`proposal.md:19`)이 실제로 지켜졌다 — `git show --stat 821b12b`에서 `add-google-oauth-onboarding/` 아래 파일은 전혀 수정되지 않았다. 기존 7개 Scenario(google-authentication 2·workspace-entry-flow 2·workspace-onboarding 2, 1라운드 보고서 기준)는 파일 수준에서 손대지 않았으므로 재검증 불필요라는 지시와 일치하며, 훑어본 결과 새 spec.md의 서술도 그 7개 Scenario의 전제(0개/1개/2개 이상 분기)와 충돌하지 않는다.
- 다만 `spec.md:9`의 Requirement 1 본문은 "소속 워크스페이스 개수와 **무관하게**"라고 적어, 0개인 사용자도 `/w/new`에 직접 접근하면 동일한 폼을 볼 수 있음을 문언상 허용한다. 반면 spec.md 최상단 Purpose(`spec.md:3`)와 `proposal.md:3`는 "이미 소속이 있는 사용자"로 더 좁게 서술한다. 코드(`w/new/page.tsx`)는 실제로 개수와 무관하게 동작하므로 **Requirement 1 텍스트와 코드는 일치**하지만, Purpose/proposal의 요약 문구가 그보다 좁다는 내부적 표현 불일치가 있다. 이는 동작 자체가 `workspace-onboarding`과 모순되거나 사용자 관찰 가능한 결함을 만들지는 않는다(0개 사용자가 `/w/new`에 도달해도 `/`의 온보딩과 동일한 결과를 얻을 뿐이다) — 판정에는 영향 없는 문서 표현상의 사소한 헐거움으로만 기록해 둔다.

## 조치가 필요한 항목

없음. 5개 Scenario 모두 충족, 1라운드 지적 2건 모두 정합, capability 경계 모순 없음.

## 판정 근거

새 change `add-additional-workspace-creation`의 spec/design/proposal/tasks는 이미 존재하는 코드(`apps/dashboard/app/w/new/page.tsx`, `onboarding-actions.ts`의 상한 검사, `WorkspaceSwitcher.tsx`의 링크 조건)를 정확히 서술하며, 대응 테스트(`new-workspace-route.test.tsx`, `onboarding-actions.test.ts`, `WorkspaceSwitcher.test.tsx`)가 5개 Scenario 전부를 검증한다. `openspec validate --strict` 통과, 전체 테스트 스위트(46 files/193 tests) 재실행 통과를 확인했다. 1라운드가 지적한 두 항목(3개 상한, `/w/new` 라우트)은 이제 정식 capability Requirement/Scenario로 명문화되어 구현과 어긋남이 없고, `Modified Capabilities: 없음` 선언대로 `add-google-oauth-onboarding`의 기존 3개 capability 파일은 손대지 않아 경계도 모순 없이 유지된다. 발견한 유일한 흠은 Purpose 문구와 Requirement 본문 사이의 사소한 표현 폭 차이이며, 이는 코드 동작이나 스펙 충족 여부에 영향을 주지 않아 조치 항목으로 올리지 않았다. 따라서 `pass`로 판정한다.

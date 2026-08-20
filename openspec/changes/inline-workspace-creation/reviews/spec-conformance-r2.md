# Spec Conformance 리뷰 — inline-workspace-creation r2

- 판정: pass
- 대상: `git diff main...HEAD` (커밋 ab6dc63) + 커밋되지 않은 working tree 수정 (`apps/dashboard/components/WorkspaceSwitcher.tsx`, `apps/dashboard/tests/WorkspaceSwitcher.test.tsx`)
- 일시: 2026-08-20T07:23:03Z

## r1 지적 사항 재검증

r1(`spec-conformance-r1.md`)이 지적한 문제: ADDED 시나리오 "인라인 폼 제출 중 검증 오류"(`spec.md:49-51`)에서 빈 문자열 케이스는 제출 버튼이 `newName.trim().length === 0`일 때 `disabled`라 `handleCreateSubmit`이 아예 호출되지 않아 THEN(폼 안 오류 표시)이 발생하지 않았다.

수정 확인:

- `apps/dashboard/components/WorkspaceSwitcher.tsx:225-231` — 제출 버튼의 `disabled` 조건이 `disabled={creating}`만 남았다. `newName.trim().length === 0` 조건이 제거되어 빈 문자열 상태에서도 클릭·Enter로 `handleCreateSubmit`(`:58-76`)이 정상 호출된다.
- `apps/dashboard/components/WorkspaceSwitcher.tsx:219-224` — 왜 클라이언트에서 빈 값을 막지 않는지, 100자 초과와 동일하게 서버(`createPersonalWorkspace`)의 `"이름은 1~100자여야 합니다."` 오류를 같은 `createError` 표시 경로(`:65-70`, `:210-217`)로 태우는지 주석으로 근거를 남겼다.
- `input`(`:191-209`)에는 `required`나 `pattern` 등 네이티브 검증 속성이 없어 브라우저 암시적 검증이 제출을 막지 않는다. `maxLength`도 없어 101자 이상 입력도 그대로 제출된다(100자 초과 케이스는 r1에서 이미 정상 확인됨, 이번에도 코드상 변경 없음).
- `apps/dashboard/app/onboarding-actions.ts:35-38` — 서버 액션이 `name.length < 1 || name.length > 100`일 때 정확히 `"이름은 1~100자여야 합니다."`를 반환. 클라이언트 수정과 별개로 이 파일은 이번 diff에 포함되지 않았고 기존 그대로다.
- 테스트: `apps/dashboard/tests/WorkspaceSwitcher.test.tsx:208-231` — "빈 문자열을 제출하면(spec: 인라인 폼 제출 중 검증 오류) 서버 검증 오류가 폼 안에 뜬다" 테스트가 폼을 열고 이름을 입력하지 않은 채 "생성" 버튼을 클릭 → `createPersonalWorkspace`가 `""`로 호출됨(`:226`) → `role="alert"`에 서버 오류 문구 노출(`:227-229`) → `push` 미호출(`:230`)을 직접 검증한다. WHEN이 명시한 정확한 트리거 조건(빈 문자열)을 재현하는 테스트다.
- 실행 확인: `pnpm test -- --run` 재실행 결과 48 files / 218 tests 전부 통과, `pnpm typecheck`(루트에서 `tsc --noEmit`) 통과, `pnpm lint`(ESLint: No issues found) 통과. 리뷰 시점에 직접 재실행해 확인함(아래 근거 참조).

이로써 빈 문자열 / 100자 초과 두 서브케이스 모두 동일한 서버 라운드트립 경로를 타 THEN(오류 표시, 입력값·폼 유지)을 충족한다. r1이 2번 항목으로 지적한 "이 시나리오를 직접 검증하는 테스트 부재"도 위 테스트 추가로 해소됐다.

## 시나리오 판정 (8개 전체 재확인)

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| 상한 이내 추가 워크스페이스 생성 / 상한 미만에서 생성 성공(전용 라우트) | 충족 | `apps/dashboard/app/w/new/page.tsx`(이번 diff 미변경, r1에서 확인됨) — 이번 리뷰 범위 밖(diff 없음), 회귀 근거 없음 |
| 상한 이내 추가 워크스페이스 생성 / 상한 도달 시 생성 거부(전용 라우트) | 충족 | `apps/dashboard/app/onboarding-actions.ts:49-54`(이번 diff 미변경) — 회귀 근거 없음 |
| 상한 이내 추가 워크스페이스 생성 / 인라인 폼에서 상한 미만 생성 성공 | 충족 | `WorkspaceSwitcher.tsx:58-76`(제출 시 `createPersonalWorkspace` 호출 후 `router.push(workspacePath(result.workspaceId))`) · 테스트 `WorkspaceSwitcher.test.tsx:163-182`(재실행 통과) |
| 상한 이내 추가 워크스페이스 생성 / 인라인 폼 제출 시점에 상한에 도달해 있으면 서버가 거부한다 | 충족 | `onboarding-actions.ts:46-54`(제출 시점 서버 재카운트) · `WorkspaceSwitcher.tsx:66-70` · 테스트 `WorkspaceSwitcher.test.tsx:184-206`(재실행 통과) — 이번 수정으로 코드 경로 변경 없음, 회귀 없음 |
| 상한 도달 시 죽은 링크를 만들지 않는다 / 상한 도달 시 진입점 숨김 | 충족 | `WorkspaceSwitcher.tsx:175`(`workspaces.length < 3` 조건, 이번 diff 미변경) · 테스트 `WorkspaceSwitcher.test.tsx:105-123`(재실행 통과) |
| 상한 도달 시 죽은 링크를 만들지 않는다 / 상한 미만에서 진입점 노출 | 충족 | `WorkspaceSwitcher.tsx:177-185`(버튼, href 없음, 이번 diff 미변경) · 테스트 `:92-103`, `:125-143`(재실행 통과) |
| 워크스페이스 스위처의 인라인 생성 폼 / 인라인 폼 진입 | 충족 | `WorkspaceSwitcher.tsx:177-209`(이번 diff 미변경 영역) · 테스트 `:125-143`, `:145-161`(재실행 통과) |
| 워크스페이스 스위처의 인라인 생성 폼 / 인라인 폼 취소 | 충족 | `WorkspaceSwitcher.tsx:52-56, 226-233(폼 취소 버튼)`(이번 diff 미변경) · 테스트 `:233-297`(재실행 통과) |
| 워크스페이스 스위처의 인라인 생성 폼 / 인라인 폼 제출 중 검증 오류 | **충족 (r1에서 미충족 → 수정 확인)** | `WorkspaceSwitcher.tsx:225-231`(disabled 조건에서 `newName.trim().length === 0` 제거) · `onboarding-actions.ts:35-38`(서버 검증 오류 문구) · 테스트 `WorkspaceSwitcher.test.tsx:208-231`(빈 문자열 직접 재현, 신규) — 100자 초과 케이스는 r1에서 이미 확인됐고 이번 diff로 변경되지 않아 그대로 유지 |

두 진입점(전용 라우트 vs 인라인 폼)이 동일 로직(`createPersonalWorkspace`)을 공유해야 한다는 요구사항 본문 조건도, 이번 수정이 `import`나 호출 방식을 바꾸지 않았으므로 r1의 "충족" 판정이 그대로 유지된다(`WorkspaceSwitcher.tsx:9`).

## 조치가 필요한 항목

없음.

## 판정 근거

r1이 미충족으로 판정한 유일한 시나리오("인라인 폼 제출 중 검증 오류")는 제출 버튼의 클라이언트 측 disabled 조건에서 빈 문자열 검사를 제거해, 빈 문자열도 100자 초과와 동일하게 서버(`createPersonalWorkspace`)로 왕복하는 경로를 타도록 고쳐졌다. 이 경로는 서버가 반환하는 `"이름은 1~100자여야 합니다."` 오류를 기존 `createError` 표시 배선 그대로 폼 안에 보여주므로 THEN("워크스페이스를 생성하지 않고 폼 안에 오류를 표시하며, 입력값과 폼은 유지된다")을 충족한다. 이를 직접 재현·검증하는 컴포넌트 테스트(`WorkspaceSwitcher.test.tsx:208-231`)도 새로 추가됐고, 리뷰 중 재실행한 `pnpm test -- --run`(48 files/218 tests)·`pnpm typecheck`·`pnpm lint`가 모두 통과했다. 나머지 7개 시나리오는 이번 diff가 건드리지 않은 영역이며 r1에서 이미 코드·테스트 대응이 확인됐고 이번 수정이 그 경로에 부작용을 준 흔적도 없다(diff는 disabled 조건 제거와 설명 주석 추가, 신규 테스트 1개 추가뿐). 8개 시나리오 전부 증거와 함께 충족되므로 `pass`로 판정한다.

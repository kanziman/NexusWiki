# Spec Conformance 리뷰 — inline-workspace-creation r1

- 판정: needs_fix
- 대상: `git diff main...feat/inline-workspace-creation` (커밋 ab6dc63)
- 일시: 2026-08-20T07:18:32Z

## 시나리오 판정

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| 상한 이내 추가 워크스페이스 생성 / 인라인 폼에서 상한 미만 생성 성공 | 충족 | `apps/dashboard/components/WorkspaceSwitcher.tsx:58-76`(제출 시 `createPersonalWorkspace` 호출 후 `router.push(workspacePath(result.workspaceId))`) · 테스트 `apps/dashboard/tests/WorkspaceSwitcher.test.tsx:163-182` |
| 상한 이내 추가 워크스페이스 생성 / 인라인 폼 제출 시점에 상한에 도달해 있으면 서버가 거부한다 | 충족 | `apps/dashboard/app/onboarding-actions.ts:46-54`(제출 시점에 서버가 재카운트해 상한 재검증) · `WorkspaceSwitcher.tsx:66-70`(에러 응답을 `createError`로 폼 안에 노출, 라우팅 안 함) · 테스트 `WorkspaceSwitcher.test.tsx:184-206`(상한 오류 메시지 노출, 입력값 유지, `push` 미호출 확인) |
| 상한 이내 추가 워크스페이스 생성 / 두 진입점이 동일 로직을 공유해야 한다(요구사항 본문) | 충족 | `WorkspaceSwitcher.tsx:9`와 `apps/dashboard/app/w/new/page.tsx:2,33`이 동일한 `createPersonalWorkspace`를 그대로 import·호출 — 로직 중복 없음 |
| 상한 도달 시 죽은 링크를 만들지 않는다 / 상한 도달 시 진입점 숨김 | 충족 | `WorkspaceSwitcher.tsx:175`(`workspaces.length < 3` 조건으로 진입점 블록 자체를 렌더링 안 함) · 테스트 `WorkspaceSwitcher.test.tsx:105-123` |
| 상한 도달 시 죽은 링크를 만들지 않는다 / 상한 미만에서 진입점 노출(인라인 폼으로 바뀌는 진입점) | 충족 | `WorkspaceSwitcher.tsx:177-185`(버튼, `href` 없음 — 클릭 시 `setCreatingOpen(true)`로 같은 자리를 폼으로 전환) · 테스트 `WorkspaceSwitcher.test.tsx:92-103`(더 이상 `menuitem`+`href="/w/new"`가 아니라 `button`임을 확인), `:125-143`(클릭 시 드롭다운 유지하며 인라인 폼 전환) |
| 워크스페이스 스위처의 인라인 생성 폼 / 인라인 폼 진입 | 충족 | `WorkspaceSwitcher.tsx:177-209`(진입점 클릭 시 드롭다운 닫지 않고 이름 입력 필드+제출/취소로 전환) · 테스트 `WorkspaceSwitcher.test.tsx:125-143`(마우스), `:145-161`(키보드 Enter) |
| 워크스페이스 스위처의 인라인 생성 폼 / 인라인 폼 취소 | 충족 | `WorkspaceSwitcher.tsx:52-56,226-233`(`resetCreateForm`이 `creatingOpen`/`newName`/`createError`를 모두 초기화, `createPersonalWorkspace` 미호출) · 테스트 `WorkspaceSwitcher.test.tsx:208-236`(취소 후 진입점 복귀, 액션 미호출, 재오픈 시 입력값 비어있음 확인), `:238-272`(드롭다운 닫힘 시에도 리셋 확인) |
| 워크스페이스 스위처의 인라인 생성 폼 / 인라인 폼 제출 중 검증 오류 | **부분 미충족** | 아래 「조치가 필요한 항목」 참조 |

## 조치가 필요한 항목

1. **빈 문자열 제출 시 스펙이 요구하는 "폼 안 오류 표시"가 실제로는 발생하지 않는다** — 델타 스펙 시나리오(`spec.md:49-51`)의 THEN은 "워크스페이스를 생성하지 않고 **폼 안에 오류를 표시**하며, 입력값과 폼은 유지된다"이다. 그런데 `WorkspaceSwitcher.tsx:221`에서 제출 버튼이 `newName.trim().length === 0`일 때 `disabled`로 비활성화되고, `input`(`:191-209`)에도 별도 클라이언트 검증이 없다. 비활성 버튼은 클릭도, 표준 HTML 암시적 제출(Enter)도 트리거하지 않으므로 — 빈 문자열(또는 공백만 입력) 상태에서는 `handleCreateSubmit`(`:58-76`)이 아예 호출되지 않고, `createError`가 설정될 경로 자체가 없다. 즉 사용자는 "제출을 시도"할 수조차 없고, 어떤 오류 메시지도 보지 못한 채 그냥 버튼이 눌리지 않는다 — 스펙 문구의 "오류를 표시" 요건이 이 서브케이스에서 충족되지 않는다.
   - 검증: `apps/dashboard/tests/WorkspaceSwitcher.test.tsx`에는 빈 문자열 제출을 다루는 테스트가 없다. 리뷰 중 임시 테스트로 재현·확인함(빈 값에서 Enter → `createPersonalWorkspace` 미호출·`alert` 미노출; 리뷰 종료 후 삭제, 저장소에 흔적 없음).
   - 100자 초과 케이스는 정상 동작함: `input`에 `maxLength`가 없어 101자 입력이 그대로 제출되고, 서버 액션(`onboarding-actions.ts:36-38`, 기존 테스트 `onboarding-actions.test.ts:72-80`에서 검증됨)이 `"이름은 1~100자여야 합니다."`를 반환하며 `WorkspaceSwitcher.tsx:66-70`이 이를 `createError`로 그대로 표시한다. 리뷰 중 임시 테스트로도 재현 확인함.
   - 제안: 두 THEN 조건(빈 문자열 / 100자 초과)이 같은 방식으로 동작하도록 정합성을 맞춘다. 예를 들어 제출 버튼 비활성화를 없애고 클라이언트에서 트림 후 빈 값이면 `createError`에 자체 메시지("이름을 입력하세요" 등)를 설정한 뒤 서버 호출을 생략하거나, 서버 라운드트립으로 통일해 항상 동일한 오류 표시 경로를 타게 한다. 어느 쪽이든 스펙 범위를 벗어나지 않는 코드 수정으로 해결 가능하다.

2. **`인라인 폼 제출 중 검증 오류` 시나리오를 직접 검증하는 컴포넌트 테스트가 없다** — `tasks.md:15-19`(1.3)는 이미 `[x]`로 완료 표시돼 있고 Verification에 "오류 응답 시 폼 유지·문구 노출을 확인"이라 적혀 있지만, `WorkspaceSwitcher.test.tsx:184-206`의 테스트는 임의의 상한 오류 문구(`"워크스페이스는 최대 3개까지 만들 수 있습니다."`)로 일반적인 오류 표시 배선만 검증할 뿐, 이 ADDED 시나리오가 명시한 트리거 조건(빈 문자열 / 100자 초과)을 실제로 재현하는 테스트는 없다. 100자 초과는 서버 액션 단위 테스트(`onboarding-actions.test.ts:72-80`, 이 change에서 수정되지 않은 기존 파일)로 간접적으로만 뒷받침되고, 빈 문자열은 위 1번 항목 때문에 애초에 이 경로로 도달하지 않는다.
   - 제안: 1번 항목을 고친 뒤, `WorkspaceSwitcher.test.tsx`에 "100자 초과 이름 제출 시 폼 안에 서버 검증 오류가 표시되고 입력값이 유지된다" 및 "빈 문자열 제출 시도 시 생성되지 않고 오류가 표시된다"를 각각 명시적으로 검증하는 테스트를 추가한다.

## 판정 근거

전체 8개 시나리오 중 7개는 코드 경로와 테스트가 명확히 대응해 `충족`으로 판정했다. 다만 ADDED 시나리오 "인라인 폼 제출 중 검증 오류"는 두 트리거 조건(빈 문자열 / 100자 초과) 중 100자 초과만 실제로 스펙대로 동작하고, 빈 문자열 쪽은 제출 버튼 비활성화로 인해 "제출"이라는 WHEN 자체가 발생하지 않아 THEN(오류 표시)이 충족되지 않는다. 이는 스펙을 다시 쓸 필요 없이 클라이언트 검증 로직을 스펙이 명시한 두 조건에 대해 동일하게 동작하도록 고치면 해결되는 문제이므로 `blocked`가 아니라 `needs_fix`로 판정한다. 나머지 항목(진입점 전환, 취소, 성공 경로, 상한 도달 거부, 진입점 숨김/노출, 두 진입점의 로직 공유)은 구현·테스트 모두 스펙과 정확히 일치한다.

## Why

기존 멤버가 소속 워크스페이스를 1개 이상 갖고 있으면 워크스페이스 스위처의 "새 워크스페이스 생성" 링크가 `/`로 이동했는데, `/`는 소속 개수에 따라 즉시 리다이렉트하거나 선택 화면만 보여줘 생성 폼에 도달할 방법이 없었다 — 항상 무동작이던 링크다. `add-google-oauth-onboarding`의 `workspace-onboarding` capability는 "RLS로 보이는 워크스페이스가 0개일 때"로 명시적으로 범위를 좁혀 정의하므로, 이미 멤버인 사용자를 위한 추가 생성 흐름은 그 capability의 연장이 아니라 별개 요구사항이다.

## What Changes

- 소속 워크스페이스 개수와 무관하게 도달 가능한 전용 라우트(`/w/new`)를 신설한다.
- 셀프서브 워크스페이스 생성에 개수 상한(1인당 최대 3개)을 둔다 — 무제한 생성 남용을 막는다.
- 워크스페이스 스위처의 "새 워크스페이스 생성" 링크를 이 라우트로 연결하고, 상한에 도달하면 링크 자체를 숨긴다.

## Capabilities

### New Capabilities

- `additional-workspace-creation`: 소속 워크스페이스가 있는 인증 사용자가 개수 상한 안에서 추가 개인 워크스페이스를 셀프서브로 만드는 흐름을 제공한다.

### Modified Capabilities

(없음 — `workspace-onboarding`의 "0개일 때" 범위는 그대로 두고 건드리지 않는다. 재사용하는 폼 컴포넌트(`WorkspaceOnboarding`)와 생성 로직(`createPersonalWorkspace`)은 구현 세부이지 그 capability의 요구사항 자체가 바뀌는 것은 아니다.)

## Impact

- `apps/dashboard/app/w/new/page.tsx` 신설.
- `apps/dashboard/app/onboarding-actions.ts`의 `createPersonalWorkspace`에 상한 검사 추가.
- `apps/dashboard/components/WorkspaceSwitcher.tsx`의 생성 링크 대상·표시 조건 변경.
- 인증 게이트는 기존 `middleware.ts`의 `/w/:path*` matcher가 그대로 커버하므로 이 change에서 다시 정의하지 않는다(`google-authentication` capability 소관).

## 참고: 사후 문서화

이 기능은 이미 구현되어 프로덕션에 배포됐다(PR #43). `spec-conformance-reviewer`가 `add-google-oauth-onboarding` 사후 리뷰에서 이 동작이 그 change의 범위 밖이라고 지적해, 별도 change로 분리해 정본 스펙을 사후에 기록한다. 코드는 이미 존재하며 이 change의 목적은 그 코드를 스펙으로 정합시키는 것이다.

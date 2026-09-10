## Why

BYOK(개인 API 키 등록 시 무제한 이용)는 `openspec/specs/usage-guardrails/spec.md`와 `openspec/specs/workspace-settings/spec.md`가 계약으로 명시하지만 실제로는 구현된 적이 없다. 워커는 항상 운영자 소유 `OPENROUTER_API_KEY`만 쓰고, 권위 있는 예산 판정 함수(`enqueue_source_job`)도 `custom_api_key`를 전혀 보지 않는다. 그 결과 사용자는 네 곳의 UI(설정·크레딧 한도 모달·계정 메뉴·사이드바)에서 "무제한"을 약속받지만, 실제로는 여전히 워크스페이스당 월 $5 상한에 그대로 걸린다. 스펙과 구현이 어긋난 채로 사용자에게 거짓 약속을 계속 노출하는 상태이므로, 지금 바로잡는다.

## What Changes

- **BREAKING**: `WorkspaceGeneralSettings.tsx`에서 커스텀 API 키 등록/삭제 UI(입력 폼·저장/삭제 버튼·"무제한" 토스트·상태 배지)를 제거한다.
- **BREAKING**: `CreditLimitModal.tsx`에서 "내 API 키 등록 시 무제한 사용" 안내와 유도 버튼을 제거한다.
- **BREAKING**: `AccountMenu.tsx`, `WorkspaceSidebar.tsx`에서 "무제한 이용 중" BYOK 배지/위젯을 제거하고, 항상 무료 크레딧 잔여량 표시로 대체한다.
- `apps/api/src/api/routers/jobs.py`의 `workspace_budget` 엔드포인트에서 `has_custom_key` 기반 `cap_micros=-1`/`remaining_micros=-1` 표시를 제거한다 — 항상 실제 `monthly_budget_micros` 기준 값을 반환한다.
- 기존에 등록된 `workspaces.custom_api_key` 값을 마이그레이션으로 전부 `null` 처리한다. 더 이상 어떤 코드 경로도 읽지 않는 외부 비밀키를 DB에 방치하지 않기 위함이다.
- `usage-guardrails`·`workspace-settings` 두 스펙에서 BYOK 관련 요구사항을 철회한다.

## Capabilities

### New Capabilities

(없음)

### Modified Capabilities

- `usage-guardrails`: "BYOK unlimited quota and limit modal integration" 요구사항 철회 — 크레딧 한도 모달은 더 이상 BYOK 유도 링크를 제공하지 않으며, 모든 워크스페이스는 항상 표준 월간 예산 상한을 따른다.
- `workspace-settings`: "BYOK custom AI API key management" 요구사항 철회 — 일반 설정 패널은 더 이상 커스텀 API 키 입력·저장·삭제 기능을 제공하지 않는다.

## Impact

- **대시보드**: `WorkspaceGeneralSettings.tsx`, `CreditLimitModal.tsx`, `AccountMenu.tsx`, `WorkspaceSidebar.tsx`, `app/w/[workspaceId]/settings/page.tsx`(초기 props 전달부)
- **API**: `apps/api/src/api/routers/jobs.py`(`workspace_budget`)
- **DB**: 신규 마이그레이션 1건(`workspaces.custom_api_key` 일괄 `null` 처리). 컬럼 자체는 남겨둔다 — 삭제는 별도 결정 없이는 하지 않는다.
- **워커**: 변경 없음(애초에 `custom_api_key`를 읽는 코드가 없었다).
- **테스트**: 위 컴포넌트·엔드포인트를 다루는 기존 테스트에서 BYOK 관련 케이스 제거/수정.

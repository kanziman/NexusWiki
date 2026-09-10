## Context

See proposal.md - Why. `workspaces.custom_api_key`는 존재하지만(마이그레이션 `0020_workspace_byok_api_key.sql`) 워커의 어떤 경로도 읽지 않는다. 노출 지점은 네 개 대시보드 컴포넌트(`WorkspaceGeneralSettings.tsx`, `CreditLimitModal.tsx`, `AccountMenu.tsx`, `WorkspaceSidebar.tsx`)와 API의 표시 로직(`jobs.py:workspace_budget`) 뿐이며, 예산 판정 SQL 함수(`enqueue_source_job`, 0009/0010)는 애초에 이 컬럼을 참조한 적이 없다 — 즉 판정 로직은 손댈 필요가 없다.

## Goals / Non-Goals

**Goals:**
- 존재하지 않는 기능에 대한 약속을 UI·스펙 양쪽에서 제거한다.
- 이미 저장된 `custom_api_key` 값을 정리한다(사용되지 않는 외부 비밀키를 DB에 방치하지 않는다).
- 예산 표시(`/workspaces/{id}/budget`)가 항상 실제 상한을 반영하도록 한다.

**Non-Goals:**
- BYOK 라우팅(개인 키로 실제 LLM 호출을 전환하는 것)을 구현하지 않는다 — 사용자와 상의해 명시적으로 배제한 방향이다.
- `workspaces.custom_api_key` 컬럼 자체를 삭제하지 않는다. 데이터만 비운다. 컬럼 제거는 이 변경의 범위 밖이며, 필요해지면 별도 change로 다룬다.
- `monthly_budget_micros` 상한값 자체(현재 워크스페이스당 월 $5)의 재설계는 다루지 않는다.

## Decisions

**결정: 라우팅을 나중에 고치는 대신 기능을 지금 제거한다.**

거부된 대안 1 — *실제 라우팅 구현*: 워커가 `custom_api_key`를 읽어 provider별로 분기하고, 예산 판정 SQL에서 BYOK 워크스페이스를 실제로 우회하도록 만드는 안. 작업량이 크고(provider 판별, 키 검증, 에러 처리, 예산 판정 함수 변경까지) 별도 change로 다룰 가치가 있는 규모다. 지금 당장 사용자에게 노출된 거짓 약속을 멈추는 것이 더 급하다.

거부된 대안 2 — *문구만 정정*: "무제한" 대신 "등록해도 현재는 운영자 예산 공유" 같은 정직한 문구로 바꾸고 입력 UI는 유지하는 안. 이렇게 해도 사용자가 "그럼 이 입력란은 왜 있나"라는 질문에 답할 수 없고, 아무 효과가 없는 기능을 굳이 유지할 이유가 없다.

**채택**: 네 UI 노출 지점을 모두 제거하고, API 표시 로직을 실제 예산 기준으로 되돌리고, 기존 데이터는 마이그레이션으로 비운다. 컬럼은 남겨 향후 실제 구현 시 재사용할 수 있게 한다.

**결정: 컬럼은 삭제하지 않고 값만 null 처리한다.**

컬럼을 완전히 삭제하면 향후 실제 BYOK를 구현할 때 새 마이그레이션과 타입 재생성이 다시 필요하다. 지금은 "쓰이지 않는 비밀값을 남겨두지 않는다"는 목표만 달성하면 충분하므로 `update ... set custom_api_key = null`로 그친다.

## Risks / Trade-offs

- [향후 실제 BYOK를 구현하고 싶을 때 사용자가 키를 다시 등록해야 함] → 이미 등록된 키가 실제로 쓰인 적이 없으므로 재등록은 최초 등록과 동일한 노력이다. 손실이 아니다.
- [마이그레이션이 프로덕션의 실제 등록 키를 지운다] → 워커가 그 값을 전혀 읽지 않았으므로 이 마이그레이션으로 인해 깨지는 기존 동작은 없다. 되돌릴 데이터가 없다(원래도 효과가 없었다).
- [컬럼을 남겨두면 나중에 또 다른 개발자가 실수로 "이미 있는 기능"이라 착각하고 UI만 다시 연결할 수 있음] → 컬럼 코멘트를 "미구현·비활성 상태"로 갱신해 마이그레이션에서 명시한다.

## Migration Plan

1. `supabase/migrations/0022_retire_byok_custom_api_key.sql`: `update public.workspaces set custom_api_key = null where custom_api_key is not null;` 및 컬럼 코멘트를 "BYOK는 UI/실제 라우팅 모두 비활성 상태 — 워커가 읽지 않는다"로 갱신.
2. 대시보드 4개 컴포넌트에서 BYOK UI 제거, `app/w/[workspaceId]/settings/page.tsx`의 `initialCustomApiKey` prop 전달 제거.
3. `jobs.py:workspace_budget`에서 `has_custom_key` 분기 제거 — 항상 `monthly_budget_micros` 기준 `cap_micros`/`remaining_micros` 계산.
4. 두 스펙 파일의 BYOK 요구사항 철회(`openspec/specs/usage-guardrails`, `openspec/specs/workspace-settings`) — `/opsx:sync`에서 반영.
5. 롤백: 코드는 git revert로 원복 가능. 마이그레이션은 데이터를 지우는 단방향 연산이라 롤백 시 값 복구는 불가능하지만, 애초에 값이 어떤 동작에도 영향을 주지 않았으므로 롤백 필요성 자체가 낮다.

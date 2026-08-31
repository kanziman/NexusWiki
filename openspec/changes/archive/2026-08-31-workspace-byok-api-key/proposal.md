## Why

초기 가입자 유치와 파워 유저(개발자, 연구자, 테크 하비스트) 유입을 가속화하기 위해, 사용자가 자신의 OpenRouter/OpenAI API 키를 워크스페이스에 직접 등록하여 월간 크레딧 소진 없이 무제한으로 AI 질의 및 소스 분석을 이용할 수 있는 BYOK (Bring Your Own Key) 지원이 필요합니다.

## What Changes

- 워크스페이스 설정 `[일반]` 탭에 **"AI 모델 및 API 키 설정 (BYOK)"** 카드 추가:
  - OpenRouter API 키(`sk-or-v1-...`) 등록, 수정, 삭제 기능
  - 저장된 API 키 마스킹 표시(`sk-or-v1-••••••••1a2b`) 및 보안 보호 (Owner 전용)
  - OpenRouter API 키 발급 바로가기 링크 제공
- 크레딧 소진 모달(`CreditLimitModal`)에 **"내 API 키 등록하고 무제한 이용하기"** 바로가기 액션 연동
- 커스텀 API 키가 등록된 워크스페이스는 사이드바 및 프로필 메뉴에 잔여 크레딧 수치 대신 **`⚡ 내 API 키 연결됨 (무제한)`** 상태 표시
- 백엔드 및 워커에서 커스텀 API 키 등록 워크스페이스의 무제한 쿼터 처리 지원

## Capabilities

### Modified Capabilities
- `workspace-settings`: 워크스페이스 소유자가 BYOK 사용자 API 키를 등록/삭제하고 마스킹된 상태를 확인할 수 있는 요구사항 추가
- `usage-guardrails`: 커스텀 API 키가 등록된 워크스페이스는 월간 크레딧 한도 차감 없이 무제한 사용을 보장하는 요구사항 추가

## Impact

- `apps/dashboard/components/WorkspaceGeneralSettings.tsx`: BYOK API 키 관리 카드 추가
- `apps/dashboard/components/CreditLimitModal.tsx`: BYOK 등록 링크 버튼 추가
- `apps/dashboard/components/WorkspaceSidebar.tsx` 및 `AccountMenu.tsx`: 커스텀 키 등록 상태 뱃지 표시
- `apps/dashboard/lib/credits.ts`: 커스텀 키 상태 헬퍼 추가
- `openspec/specs/workspace-settings/spec.md` 및 `openspec/specs/usage-guardrails/spec.md`: delta 스펙 반영

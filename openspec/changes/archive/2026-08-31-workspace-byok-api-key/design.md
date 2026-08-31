## Context

현재 워크스페이스는 기본 무료 500 크레딧(`monthly_budget_micros`)을 기반으로 동작합니다.
초기 가입자 유치 및 파워 유저를 위해, 워크스페이스 소유자가 자신의 OpenRouter/OpenAI API 키를 등록하면 크레딧 제한 없이 무제한으로 AI 위키 생성과 질의를 이용할 수 있는 BYOK 구조를 도입합니다.

## Goals / Non-Goals

**Goals:**
- 워크스페이스 설정 화면(`WorkspaceGeneralSettings.tsx`)에서 OpenRouter API 키 등록, 마스킹 조회, 수정, 삭제 지원.
- 키 등록 여부에 따라 `CreditLimitModal`, `WorkspaceSidebar`, `AccountMenu`에서 `무제한 (내 API 키)` 상태를 일관되게 렌더링.
- API 키는 소유자에게만 노출/수정 가능하도록 권한 격리 및 안전한 마스킹(`sk-or-v1-••••••••1a2b`) 처리.

**Non-Goals:**
- 키 제공자별(Anthropic, Google, Mistral 등) 다중 엔드포인트 커스텀 설정 (OpenRouter 표준 단일 통합 엔드포인트 지원에 집중).

## Decisions

1. **API 키 관리 및 마스킹**:
   - `workspaces` 테이블의 `custom_api_key` 컬럼을 활용하며, 프론트엔드 및 일반 조회 시 앞뒤 4자리 외에는 마스킹 처리하여 안전성을 유지합니다.
2. **BYOK 상태의 쿼터 무제한 처리**:
   - `custom_api_key`가 존재하는 워크스페이스는 `budget.cap_micros`가 무제한(`-1` 또는 `unlimited: true`)으로 간주되어 402 가드레일이 발생하지 않습니다.
3. **사용자 경험 (UX)**:
   - 크레딧 소진 모달(`CreditLimitModal`)에서 *"내 API 키 등록하고 무제한 이용하기"* 링크를 제공하여 자연스러운 전환을 유도합니다.

## Risks / Trade-offs

- [사용자가 유효하지 않은 API 키를 입력할 위험] → 키 형식 사전 검증(`sk-or-v1-...` 등 접두사 및 길이 검사) 및 실패 시 친절한 오류 메시지 제공.

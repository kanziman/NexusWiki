# Proposal: 무료 사용자 크레딧 쿼터 및 사용량 한도 안내 시스템

## 1. 배경 및 문제 정의
현재 NexusWiki가 공개 배포될 경우, 무료 사용자가 소스 등록(파싱·임베딩·컴파일) 및 질문하기(RAG LLM 질의)를 무제한으로 요청하여 LLM/임베딩 API 비용이 급격히 증가할 수 있습니다.
시스템 내부에 `monthly_budget_micros` 및 402 `budget_exceeded` 차단 메커니즘이 존재하지만, 사용자 관점에서:
1. 신규 생성 시 기본 무료 예산 상한이 안정적인 금액($1.00 = 1,000,000 micros)으로 표준화되어야 함.
2. 질문하기(`AskConversation`) 및 소스 업로드(`Dropzone`)에서 402 초과 발생 시 raw 에러 대신 "이번 달 무료 크레딧을 모두 소진했습니다"라는 명확하고 친절한 안내 모달/배너가 노출되어야 함.
3. 운영/설정 패널에서 현재 사용량과 남은 크레딧을 직관적으로 확인할 수 있어야 함.

## 2. 해결 방안
- **신규 워크스페이스 무료 크레딧 기본값 보장**: 생성 시 `monthly_budget_micros: 1000000` ($1.00, 약 50~100회 질의 및 소스 처리 가능)
- **한도 도달 시 `CreditLimitModal` 및 인라인 안내 UI**:
  - 질문하기 스트리밍 / 소스 업로드 API에서 402 `budget_exceeded` 발생 시 사용자 친화적인 무료 크레딧 소진 안내 모달 제공
  - 다음 달 1일 초기화 안내 및 사용량 관리 링크 제공
- **설정/운영 화면에 무료 크레딧 사용량 진행 바(Progress Bar) 표시**:
  - 현재 소진 금액 / 무료 제공 한도 시각화

## 3. 영향 범위
- `apps/dashboard/components/CreditLimitModal.tsx` (신규)
- `apps/dashboard/components/AskConversation.tsx` (402 에러 처리 및 모달 트리거)
- `apps/dashboard/components/Dropzone.tsx` (402 에러 처리 및 모달 트리거)
- `apps/dashboard/components/OperationsPanel.tsx` / `WorkspaceGeneralSettings.tsx` (사용량 게이지/안내)
- `openspec/specs/usage-guardrails/spec.md` (델타 스펙 동기화)

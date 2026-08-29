## Why

Ask의 첫 질문은 답변과 인용이 완성된 뒤에만 스레드로 저장된다. 사용자가 생성 중 홈 대시보드처럼 다른 워크스페이스 라우트로 이동했다가 Ask로 돌아오면 URL과 서버 상태가 원래 대화를 식별하지 못해 빈 새 대화 화면이 열린다.

## What Changes

- 첫 질문을 제출하는 즉시 작성자·워크스페이스 소유의 Ask 스레드와 진행 중 턴을 생성한다.
- 생성 직후 Ask URL을 해당 스레드로 정규화하여 라우트 이동 뒤에도 원래 대화를 다시 연다.
- 진행 중 턴을 서버에서 조회·표시하고, 답변 생성이 끝나면 같은 턴을 최종 답변·인용·상태로 확정한다.
- 기존 완료 턴의 이중 인용, `done` 이벤트의 완료 보장, 작성자·멤버십 RLS와 단건 grounded Ask 의미를 보존한다.

## Capabilities

### New Capabilities

- 없음.

### Modified Capabilities

- `ask-thread-history`: 첫 질문의 즉시 스레드·진행 중 턴 생성과 라우트 복귀 복원 요구사항을 추가한다.

## Impact

- `supabase/migrations/`: 진행 중 Ask 턴의 상태와 안전한 생성·확정 경로를 지원한다.
- `apps/api/src/api/routers/ask.py`, `apps/api/src/api/services/ask.py`: 요청자 JWT로 초기 스레드/턴을 만들고 SSE 생성 흐름에서 최종 상태를 확정한다.
- `apps/dashboard/components/AskConversation.tsx`, `apps/dashboard/lib/ask-threads.ts`: 초기 스레드 식별자를 URL에 반영하고 재진입 때 진행 중·완료 턴을 복원한다.
- API·대시보드 테스트: 라우트 이동과 재진입, 최종 인용, RLS·멱등성을 회귀 검증한다.

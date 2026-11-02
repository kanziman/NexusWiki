## 1. Ask 스트림 결함 수정

- [ ] 1.1 Ask 스트림의 깨진 프레임과 중간 오류를 오류로 종결하고, 인용 지표를 위조 제거 후 텍스트로 계산하며, 실패한 검색 채널을 `meta`로 전달한다 (D6, 저장은 4.1에서 다룬다)
  - Given: 답변 스트림 중 깨진 프레임이나 오류 프레임이 오거나, 위조 앵커만 달린 문장이 있거나, 한 검색 채널이 실패했다
  - When: 멤버의 Ask가 진행된다
  - Then: 턴은 `error`로 종결되어 부분 답변이 저장되지 않고, 위조 문장은 이중 인용으로 계산되지 않으며, 실패 채널만 안내되고 비활성 그래프 채널은 안내되지 않는다
  - 검증: `uv run pytest apps/api/tests/test_ask_router.py apps/api/tests/test_ask_citations.py packages/core/tests/test_sentences.py` · `cd apps/dashboard && pnpm test -- AskConversation`
  - GitHub: https://github.com/kanziman/NexusWiki/issues/158

## 2. 요청 trace

- [x] 2.1 API가 trace를 발급해 모든 응답 헤더와 로그에 남기고, 질의 임베딩과 LLM 내부 호출로 전달해 워커 로그까지 잇는다 (D2)
  - Given: 클라이언트가 위조한 `X-Trace-Id`로 API를 호출하거나, 처리되지 않은 예외가 나거나, 이전 버전 API가 헤더 없이 워커를 호출한다
  - When: 요청이 처리된다
  - Then: 응답마다 서버가 발급한 값이 헤더에 있고, API와 워커 로그의 값이 같으며, 헤더 없는 내부 호출은 거부되지 않고 워커가 값을 발급한다
  - 검증: `uv run pytest apps/api/tests/test_trace_middleware.py apps/worker/tests/test_query_embedding.py apps/worker/tests/test_llm_stream.py packages/core/tests/test_logging_redaction.py`
  - GitHub: https://github.com/kanziman/NexusWiki/issues/159

- [x] 2.2 수집 잡이 시작 요청의 trace를 저장하고 체인 전 단계와 재시도로 물려주며, 잡 시작 시각을 남긴다 (D3)
  - Given: 멤버가 원문을 등록해 체인이 돌고, 그중 잡이 실패해 재시도되거나 같은 대상이 다시 인큐된다
  - When: 체인이 끝까지 진행된다
  - Then: 모든 단계 잡의 `trace_id`가 같고 재시도와 중복 인큐에서 값이 바뀌지 않으며, 마이그레이션 이전 잡은 값 없이 정상 처리되고 `last_claimed_at`으로 소요 시간을 계산할 수 있다
  - 검증: `uv run pytest apps/worker/tests/test_queue.py apps/worker/tests/test_handlers.py apps/api/tests/test_sources_router.py apps/api/tests/test_pipeline_e2e.py` (로컬 Supabase 필요)
  - GitHub: https://github.com/kanziman/NexusWiki/issues/160

## 3. 비용 회계

- [ ] 3.1 `LlmGateway`로 잡 경로의 LLM·임베딩 호출을 모아 시도별 사용량을 즉시 기록하고, 충돌 판정 비용을 처음으로 기록한다 (D4)
  - Given: 컴파일이 검증 실패 후 재시도하거나 전 시도가 실패하고, 충돌 판정이 후보 쌍을 판정한다
  - When: 공급자가 사용량을 보고한다
  - Then: `usage_events` 합계가 공급자 보고 비용의 합과 일치하고 모든 행에 trace가 있으며, 요청 본문과 재시도 흐름은 그대로이고, 핸들러가 공급자 함수를 직접 부르면 구조 테스트가 실패한다
  - 검증: `uv run pytest apps/worker/tests/test_llm.py apps/worker/tests/test_llm_gateway.py apps/worker/tests/test_handlers.py apps/worker/tests/test_embedding.py`
  - GitHub: https://github.com/kanziman/NexusWiki/issues/161

- [x] 3.2 Ask 경로에서 중단된 스트림과 질의 임베딩의 사용량을 기록한다 (D5)
  - Given: 클라이언트가 스트림 도중 연결을 끊거나, 멤버가 질의를 검색한다
  - When: 호출이 끝나거나 취소된다
  - Then: 중단된 호출은 `incomplete`로 한 건 기록되고, 질의 임베딩은 같은 trace로 기록되며, 기록 실패는 경고만 남기고 검색을 실패시키지 않는다
  - 검증: `uv run pytest apps/worker/tests/test_llm_stream.py apps/worker/tests/test_query_embedding.py apps/worker/tests/test_worker_main.py apps/api/tests/test_retrieval_service.py`
  - GitHub: https://github.com/kanziman/NexusWiki/issues/162

## 4. 결정과 턴 기록

- [x] 4.1 Ask 턴에 trace, 구간 시간, 인용 지표, Router 결정을 본문 없이 저장한다. Router는 기록만 한다 (D1, D3, D7)
  - Given: 멤버가 제목과 일치하는 질문, 근거 없는 질문, 일반 질문을 하거나 같은 `client_turn_id`로 재전달한다
  - When: 턴이 종결된다
  - Then: 각 턴의 `control_report`에 결정과 구간이 남지만 LLM 호출 여부는 기존과 같고, 재전달은 원래 trace로 모이며, `citations` 계약과 턴 복원은 변하지 않는다
  - 검증: `uv run pytest apps/api/tests/test_ask_router.py apps/api/tests/test_ask_thread_history.py apps/api/tests/test_ask_thread_history_isolation.py packages/core/tests/test_router.py` (로컬 Supabase 필요)
  - GitHub: https://github.com/kanziman/NexusWiki/issues/163

- [x] 4.2 컴파일 잡마다 입력 지문과 Router 결정을 사용량 메타데이터에 기록한다. 컴파일은 그대로 실행한다 (D7)
  - Given: 입력 지문이 직전 성공과 같거나, 입력이 예산에서 잘리거나, 이전 지문을 읽지 못한다
  - When: 컴파일 잡이 실행된다
  - Then: 각각 `SKIP_UNCHANGED`, `TRUNCATED`, `STANDARD`가 기록되고 어느 경우에도 LLM 호출은 일어나며 잡은 지문 읽기 실패로 실패하지 않는다
  - 검증: `uv run pytest apps/worker/tests/test_handlers.py packages/core/tests/test_router.py`
  - GitHub: https://github.com/kanziman/NexusWiki/issues/164

## 5. Control Room 추적 탭

- [x] 5.1 멤버가 `/w/[workspaceId]/control`에서 자신의 Ask trace 목록과 상세를 보고, 다른 사람의 Ask trace는 403을 받는다 (D9)
  - Given: 작성자, 같은 워크스페이스의 owner와 viewer, 비멤버, 멤버십을 잃은 작성자가 있다
  - When: 각자 탭을 열거나 trace 식별자로 상세를 요청한다
  - Then: 작성자만 단계별 시간, 토큰, 비용을 보고 합계가 사용량 행과 일치하며, 나머지는 403을 받고 응답에 본문이 없다. 이후 Step 탭은 빈 상태만 표시한다
  - 검증: `uv run pytest apps/api/tests/test_control_router.py apps/api/tests/test_tenant_isolation_full_path.py` (로컬 Supabase 필요) · `cd apps/dashboard && pnpm test -- ControlRoom && pnpm typecheck && pnpm lint`
  - GitHub: https://github.com/kanziman/NexusWiki/issues/165

- [ ] 5.2 editor 이상이 수집 trace 상세와 사용자를 드러내지 않는 Ask 집계를 본다 (D9)
  - Given: 진행 중이거나 실패한 수집 체인과 여러 멤버의 Ask 턴이 있다
  - When: editor, viewer, 비멤버가 각각 조회한다
  - Then: editor는 단계 상태와 정제된 오류, 집계를 보고 집계에 사용자·스레드·trace 식별자가 없으며, viewer와 비멤버는 수집 trace와 집계를 받지 못한다
  - 검증: `uv run pytest apps/api/tests/test_control_router.py` (로컬 Supabase 필요) · `cd apps/dashboard && pnpm test -- ControlRoom`
  - GitHub: https://github.com/kanziman/NexusWiki/issues/166

## 6. 외부 관측

- [x] 6.1 자격 증명이 있을 때만 trace를 본문 없이 Langfuse로 내보낸다 (D8)
  - Given: 키가 없거나, 외부 서비스가 실패하거나, 고유 문자열이 담긴 질문과 원문이 전체 경로를 지나거나, 워커가 SIGTERM을 받는다
  - When: 처리와 내보내기가 진행된다
  - Then: 키가 없으면 비활성으로 정상 기동하고, 실패는 결과와 사용량에 영향을 주지 않으며, 전송 값과 로그에 고유 문자열과 비밀 키가 없고, flush는 제한 시간 안에 끝난다
  - 검증: `uv run pytest packages/core/tests/test_observability.py packages/core/tests/test_logging_redaction.py apps/worker/tests/test_worker_main.py apps/worker/tests/test_settings.py`
  - GitHub: https://github.com/kanziman/NexusWiki/issues/167

## 7. 공개 쇼케이스와 정리

- [x] 7.1 합성 증거로 통제 전후를 보여주는 `/showcase/controlled-ai`를 제공한다 (D10)
  - Given: 비로그인 방문자와 세션이 있는 사용자가 있고, Step 1 시나리오의 증거 파일이 생성되어 있다
  - When: 쇼케이스를 연다
  - Then: 같은 합성 내용이 로그인 이동이나 DB·API 요청 없이 표시되고, 항목마다 시나리오와 커밋이 있으며, 합성임을 명시하고 Step 2~4는 준비 중으로 표시한다. 증거에 UUID, 이메일, 자격 증명 형태가 있으면 테스트가 실패한다
  - 검증: `uv run pytest apps/worker/tests/test_controlled_ai_evidence.py` · `cd apps/dashboard && pnpm test -- ControlledAiShowcase && pnpm build`
  - GitHub: https://github.com/kanziman/NexusWiki/issues/168

- [x] 7.2 4채널을 정본으로 문서를 맞추고 배포 기록을 남긴다
  - Given: `.claude/CLAUDE.md`, `README.md`, `docs/reference/stack.md`에 5채널 서술이 있고 새 환경 변수와 마이그레이션이 추가되었다
  - When: 문서를 갱신한다
  - Then: 운영 검색을 4채널과 선택적 그래프로 서술하고, 기본 정책에서 그래프 RPC를 호출하지 않음을 테스트가 보장하며, `.env.sample`과 `stack.md`, 마이그레이션 기록이 실제와 일치한다
  - 검증: `uv run pytest apps/api/tests/test_retrieval_service.py` · `openspec validate ai-control-flow-accounting --strict`
  - GitHub: https://github.com/kanziman/NexusWiki/issues/169

- [ ] 7.3 코드를 커밋한 뒤 공개 증거의 `after.commit`을 실제 해시로 갱신한다 (D10, 7.1에서 분리)
  - Given: 측정에 쓰인 코드가 아직 커밋되지 않아 증거의 `after.commit`이 `uncommitted`이다
  - When: `/create-pr`로 코드를 커밋한 뒤 증거를 다시 생성한다
  - Then: 쇼케이스의 모든 항목이 수정 후 커밋 해시를 표시한다. 커밋되지 않은 코드의 측정값에 HEAD를 적으면 그 커밋에 없는 코드의 값을 공개하게 되므로, 작업 트리가 깨끗할 때만 해시가 기록된다
  - 검증: `uv run python apps/worker/tests/test_controlled_ai_evidence.py measure <out> && uv run python apps/worker/tests/test_controlled_ai_evidence.py write after <out>` · `uv run pytest apps/worker/tests/test_controlled_ai_evidence.py`
  - GitHub: https://github.com/kanziman/NexusWiki/issues/168

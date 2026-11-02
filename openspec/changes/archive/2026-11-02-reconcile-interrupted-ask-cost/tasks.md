## 1. 호출 전 예산 확보와 제한

- [x] 1.1 모델별 확보 정책과 영속 예약을 실제 Ask 승인 경로에 연결한다 (D1~D4)
  - Given: 검토된 모델별 정책과 제한된 잔여 예산이 있고 여러 Ask가 동시에 들어온다
  - When: 내부 인증·정책·속도 제한을 통과한 호출이 공급자 호출을 시도한다
  - Then: DB에서 원자적으로 승인된 호출만 공급자에 도달하고 동일 call_id는 중복 예약되지 않으며, 정책 누락·입력 초과·DB 실패는 공급자 호출 전에 거부된다. 예산 부족은 기존 402로 전달되고 출력 토큰 제한이 실제 공급자 요청에 실린다
  - 포함: 예약·정산 테이블과 최소 권한, 모델 정책 검증·환경 변수 안내, 워커 발급 call_id·UTC 귀속 월, 공통 예산 집계와 수집 인큐 연결. 미정산 관측 비용과 확보액은 max로 계산한다. 신규 Ask를 승인하지 않은 요청은 공급자를 호출하지 않는다
  - 검증: `uv run pytest apps/worker/tests/test_ask_cost_accounting.py apps/worker/tests/test_settings.py apps/worker/tests/test_llm.py apps/worker/tests/test_llm_stream.py apps/api/tests/test_ask_router.py` · `docker exec -i supabase_db_NexusWiki psql -U postgres -d postgres -v ON_ERROR_STOP=1 < supabase/tests/ask_cost_accounting.sql` (신규 테스트 파일, 로컬 Supabase 필요)
  - 규모: 반나절~하루. 운영 DB 적용은 포함하지 않는다
  - GitHub: https://github.com/kanziman/NexusWiki/issues/177

## 2. 정상 완료와 중단 호출 회계

- [x] 2.1 정상 완료는 확정 정산하고 중단 호출은 추적 가능한 미해결 상태로 남긴다 (1.1 이후, D1~D4)
  - Given: 예약된 Ask가 정상 완료·중단·최종 비용 누락 중 하나로 끝난다
  - When: 전송 의도, 응답 헤더 또는 프레임의 generation ID, 관측 사용량을 기록한다
  - Then: 정상 확정액은 한 번만 반영되고 기존 usage 행은 보존되며, 명시적 0과 누락을 구분하고 하향·상향 정산도 음수 usage 행 없이 계산된다. 전송 전 취소는 근거를 남겨 해제하고, 전송 여부가 불명확하면 예약을 유지한다
  - 포함: 공급자 경계의 ID 콜백, 원자적 정산 RPC, 관측 usage와 call_id 연결, 정상 완료·반복 정산·비용 초과 및 월 경계 처리. 공급자 호출 자동 재전송 금지
  - 검증: `uv run pytest apps/worker/tests/test_ask_cost_accounting.py apps/worker/tests/test_llm_stream.py apps/worker/tests/test_llm_gateway.py apps/worker/tests/test_llm.py apps/worker/tests/test_controlled_ai_evidence.py` · `docker exec -i supabase_db_NexusWiki psql -U postgres -d postgres -v ON_ERROR_STOP=1 < supabase/tests/ask_cost_accounting.sql`
  - 규모: 반나절~하루
  - GitHub: https://github.com/kanziman/NexusWiki/issues/178

## 3. 재시작 가능한 공급자 비용 대조

- [x] 3.1 기존 워커에서 미해결 호출을 임대해 공급자 확정 비용과 대조한다 (2.1 이후, D4~D5)
  - Given: generation ID가 있는 중단 호출, ID 없는 호출, 만료된 in-flight 및 일시 장애가 있다
  - When: 대조 루프가 재시작되거나 여러 워커가 같은 호출을 처리한다
  - Then: 유효한 종료·비용 근거가 있는 호출만 한 번 정산하고, 조회 오류·ID 불일치·미종결 응답은 예약을 유지한다. 임대 만료 후 복구되며 재시도 한도 초과는 manual_review로 드러나고 비용 0 해제로 바뀌지 않는다
  - 포함: 제한된 동시성·요청 시간·배치·지수 지연, 임대 claim RPC, 종료 처리, 본문 없는 fixture 기반 generation 조회와 허용 필드 검사. 모델·ID·금액 검증 및 비밀 누출 방지
  - 검증: `uv run pytest apps/worker/tests/test_ask_cost_reconciliation.py apps/worker/tests/test_worker_main.py apps/worker/tests/test_ask_cost_accounting.py packages/core/tests/test_logging_redaction.py` · `docker exec -i supabase_db_NexusWiki psql -U postgres -d postgres -v ON_ERROR_STOP=1 < supabase/tests/ask_cost_accounting.sql` (reconciliation 테스트는 신규 파일)
  - 규모: 반나절~하루. 실제 유료 공급자 호출은 포함하지 않는다
  - GitHub: https://github.com/kanziman/NexusWiki/issues/179

## 4. 비용 표시와 접근 경계

- [x] 4.1 Control Room과 기존 비용 소비자에 확정·미확정·예산 판정액을 일관되게 제공한다 (3.1 이후, D2, D6)
  - Given: 정상·미해결·정산 완료 호출과 작성자·다른 멤버·비멤버·멤버십 상실자가 있다
  - When: 비용 화면·집계·trace 상세를 조회하거나 비용 RPC에 직접 접근한다
  - Then: 승인된 조회만 비용과 상태를 받고 타인 Ask 상세는 403이며, 호출 수·토큰·비용을 중복 계산하지 않고 임시 확보액을 실제 청구액처럼 표시하지 않는다. 정산 테이블과 generation ID는 사용자에게 직접 노출되지 않는다
  - 포함: 설정·운영 snapshot·Control Room·인큐·Ask의 비용 집계 소비자 전수 확인, 요청자 JWT 경계의 최소 권한 RPC, 집계의 개인 식별자 배제, UI 테스트. 수집 인큐의 예약 반영 동작은 1.1에서 도입한 것을 회귀 검증한다
  - 검증: `uv run pytest apps/api/tests/test_control_router.py apps/api/tests/test_tenant_isolation_full_path.py apps/worker/tests/test_ask_cost_accounting.py` · `cd apps/dashboard && ./node_modules/.bin/vitest run tests/ControlRoom.test.tsx tests/OperationsPanel.test.tsx --testTimeout=30000 && pnpm typecheck && pnpm lint`
  - 규모: 반나절~하루. 추가 비용 소비자인 AccountMenu의 기존 테스트도 실행했다: `cd apps/dashboard && ./node_modules/.bin/vitest run tests/AccountMenu.test.tsx --testTimeout=30000`
  - GitHub: https://github.com/kanziman/NexusWiki/issues/180

## 5. 통합 검증과 운영 전환 준비

- [x] 5.1 반복 중단·복구의 전체 회계 경로를 검증하고 전환·복구 절차를 남긴다 (4.1 이후, D1~D6)
  - Given: 작은 예산의 워크스페이스, 공급자 fixture, 진행 중 호출과 미해결 예약이 있다
  - When: 반복 중단·동시 승인·워커 재시작·사후 정산·월 경계를 연속 실행한다
  - Then: 무료 반복 승인이 차단되고 관측 이력은 불변이며 확정액·미확정 점유·예산 판정액이 일치한다. 운영 문서에 모델별 가격 검토 근거, 실제 청구 상한 미보장, Ask 중지·DB 선적용·버전 전환·재개 및 롤백 제한이 명시된다
  - 검증: `uv run pytest` · `uv run ruff check apps packages` · `uv run ruff format --check apps packages` · `cd apps/dashboard && ./node_modules/.bin/vitest run --testTimeout=30000 && pnpm typecheck && pnpm lint && pnpm build` · `openspec validate reconcile-interrupted-ask-cost --strict`
  - 완료 후 저장소 계약에 따라 리뷰 2종을 실행하고 통과 후 정본 동기화·strict 검증·아카이브를 진행한다. 운영 중지·DB push·유료 호출·PR 머지는 이 task가 승인하지 않는다
  - 규모: 반나절~하루
  - GitHub: https://github.com/kanziman/NexusWiki/issues/181

# 재개 안내: ai-control-flow-accounting

2026-11-02에 Windows 컴퓨터에서 Mac으로 작업을 옮기면서 작성했다. 에이전트 메모리는 컴퓨터마다 따로 있어서, 재개에 필요한 내용을 여기에 옮겼다. 이 작업을 끝내고 PR을 만들기 전에 이 파일을 지운다.

## 현재 상태

- 브랜치는 `feat/ai-control-flow-accounting`이고, 기준 커밋은 `79b68fe`다. PR은 아직 없다.
- **이 커밋은 중간 저장이다.** 리뷰 게이트 1라운드가 끝나지 않았으므로 PR로 진행하면 안 된다.
- 체크박스의 정본은 `tasks.md`다. 리뷰에서 일부 동작이 빠졌다고 지적된 1.1, 3.1, 5.2는 미완료로 되돌렸다. 7.3은 코드 커밋 뒤에 끝나는 작업이라 아직 미완료다.
- 클라우드에는 아무것도 적용하지 않았다.

## 리뷰 게이트

- `reviews/tenant-isolation-reviewer-r1.md`: **`blocked`**. 치명 1건, 보통 3건, 낮음 5건이다. 사람의 결정 없이 PR로 진행하면 안 된다.
- `reviews/spec-conformance-reviewer-r1.md`: `needs_fix`. 46개 시나리오 중 43개가 충족이다.
- 최대 3라운드다. 3라운드에서도 `pass`가 아니면 `blocked`로 확정하고 사람에게 넘긴다.

## ⚠️ 가장 먼저 고칠 결함

**로그인 없이 다른 워크스페이스의 `usage_events`에 비용을 기록할 수 있다.** 이번 변경에서 생긴 문제이고, 격리 리뷰의 지적 1이다.

- `apps/api/src/api/routers/retrieval.py`의 `retrieve`가 JWT와 멤버십을 확인하지 않고 `service.retrieve`를 부른다. 서비스는 첫 RPC보다 먼저 임베딩을 호출하고, 이번 변경으로 경로의 워크스페이스 ID가 `X-Workspace-Id`로 워커에 전달된다. 워커는 `service_role`로 그 워크스페이스에 비용 행을 쓴다.
- 라우터에 게이트가 없음은 코드에서 직접 확인했다. 재현은 리뷰어가 로컬 스택에서 했고, `Bearer not-a-jwt`로 200을 받으면서 피해 워크스페이스에 `usage_events` 행이 생겼다.
- 이 합계는 월 상한 판정에 들어가므로, 공격자가 피해 워크스페이스의 수집과 Ask를 막을 수 있다.
- 조치: `service.retrieve` 전에 `has_workspace_role(viewer)`를 확인하고, 실패하면 `WorkspaceForbidden`을 던진다.
- 회귀 테스트: 비멤버와 위조 토큰 각각에 대해 임베딩 호출 0회, 피해 워크스페이스 `usage_events` 0행을 단언해 `test_tenant_isolation_full_path.py`에 더한다. 지금 이 스위트에는 `/retrieval` 행이 없다.
- 클라우드 마이그레이션과 코드 배포 전에 반드시 고쳐야 한다. 지금은 어디에도 배포되지 않았다.

## 다음에 할 일

먼저 위 결함을 고친 뒤, `tenant-isolation-reviewer-r1.md`의 나머지 지적 8건을 읽고 처리한다. 그중 치명 다음으로 큰 것은 다음 세 건이다. 코드에서 다시 확인하고 고친다.

- **지적 2:** 작성자가 자신의 `control_report`에 큰 수를 넣으면 `ask_trace_aggregate`가 `22003`으로 실패해 editor의 집계가 500이 된다. 클라우드에 아직 적용하지 않았으므로 `0026`을 고칠지 `0027`로 고칠지 정한다.
- **지적 4:** 워커 `main`이 묶은 `workspace_id="bootstrap"`을 리스너가 물려받아, 헤더 없는 질의 임베딩이 건너뛰지 않고 `bootstrap`으로 기록을 시도한다.
- **지적 5:** 작성자가 `ask_messages.trace_id`를 임의의 값으로 바꿀 수 있다.

이어서 `spec-conformance-reviewer-r1.md`의 조치 항목 다섯 개를 처리한다. 코드에서 지적이 맞는지 확인했고 아직 고치지 않았다.

1. **Ask 턴 미종결** (`apps/api/src/api/services/ask.py`, task 1.1)
   - `_delta_text`는 JSON 파싱 실패만 잡는다. `choices`, `delta`, `content`의 형태를 검사해 `_AnswerStreamFailed`를 던진다. `content`가 문자열이 아니면 지금은 try 밖의 `join`에서 `TypeError`가 난다.
   - 근거 조회, 근거 본문 조회, 템플릿 선택과 렌더가 try 밖이다. 라우터가 `start_ask_turn`을 부른 뒤라 HTTP 오류로 바꿀 수 없으므로, 예외를 잡아 `error` 상태로 종결한다.
   - 근거 조회가 실패하면 `result`와 `route`가 없으므로 `_control_report`가 `route` 없음을 받아야 한다. 집계 RPC(`0026`)는 결정이 없는 행을 이미 거른다.
   - 대시보드는 오류 토큰을 문자열로 분기하지 않는다. 새 토큰을 더해도 되는지는 `grep`으로 다시 확인한다.
2. **비용 기록 누락** (`apps/worker/src/worker/llm.py`, `embedding.py`, `llm_gateway.py`, task 3.1)
   - `_read_completion`이 `content: null`이나 빈 `choices`에서 먼저 예외를 던져 `on_attempt`에 닿지 못한다. 사용량 읽기와 내용 읽기를 나누고 기록을 먼저 한다.
   - `embed_texts`는 공급자나 차원이 맞지 않으면 비용 계산 전에 예외를 던지고, 게이트웨이는 정상 반환 뒤에만 기록한다. `complete_structured`처럼 콜백을 받게 한다. `test_handlers.py:170`과 `test_worker_main.py:167`의 대역도 함께 고친다.
3. **Control Room 표시 누락** (`apps/dashboard/components/ControlRoom.tsx`, task 5.2)
   - API는 호출별 `route`를 주지만 `Call` 타입과 표에 없어 컴파일 결정이 화면에 나오지 않는다.
   - 최종 상태도 상세 패널에 없고 목록 배지에만 있다.
4. **`after.commit` 방어** (`apps/worker/tests/test_controlled_ai_evidence.py`)
   - 지금 테스트는 `uncommitted`를 계속 허용해 7.3을 잊어도 배포된다. 측정 대상 코드가 커밋되어 있는데 증거가 `uncommitted`이면 실패하는 테스트를 더한다.
5. **테스트 공백**
   - `PipelineHarness.drain`이 잡의 trace를 묶지 않고 `conflict_check`를 실행하지 않는다. `queue.process_next_job`처럼 잡의 trace를 묶게 고친 뒤, 전 단계 잡과 사용량 행의 trace가 같은지 단언한다. `parse`가 직접 인큐하는 `embed` 잡도 여기서 함께 검증된다.
   - `supabase/tests/0023_job_trace.sql`의 계약 5는 제목에 회수를 포함하지만 `reap_stale_jobs`를 호출하지 않는다.
   - 재실행해도 앞선 사용량 행이 덮어써지지 않는다는 테스트를 더한다.

그 뒤 순서는 다음과 같다.

1. 2라운드 리뷰(`spec-conformance-reviewer`, `tenant-isolation-reviewer`)를 병렬로 돌린다.
2. 둘 다 `pass`이면 사용자 승인을 받아 `/create-pr`을 진행한다.
3. 커밋 뒤 7.3을 수행하고, 이 파일을 지운다.

## 사람이 결정할 사항

- **비멤버 `/retrieval`의 응답 계약:** 지금은 200과 빈 근거를 돌려준다. 위 결함을 고치면 403이 되는 계약 변경이므로 승인이 필요하다. delta spec에 시나리오도 더해야 한다. 위조 토큰은 게이트에서 PostgREST 오류가 되어 현재 매핑으로는 500이 된다는 것이 리뷰어의 판단이며, 401로 맞출지도 함께 정한다.
- **API의 `LANGFUSE_SECRET_KEY`:** `apps/api/src/api/settings.py`의 "쓰는 일만 할 수 있다"는 주석은 틀렸다. SDK에서 같은 키로 trace 읽기와 삭제 API가 노출되어, API가 침해되면 전 테넌트의 비본문 메타데이터를 읽고 지울 수 있다. 서버 측 권한 범위는 호출해 확인하지 않았다. (가) 주석을 고치고 위험을 감수해 유지하거나, (나) `export_ask_turn`을 내부 토큰으로 워커에 위임해 API에서 키를 없앤다.
- **클라이언트 연결 끊김:** 델타 수신 뒤 연결이 끊기면 턴이 `streaming`으로 남는다. 기준 커밋에도 있는 동작이다. 스펙의 "every started Ask turn"을 공급자 실패로 좁힐지, 후속 작업으로 분리할지 정해야 한다.
- **squash 뒤의 `after.commit`:** PR 브랜치 해시는 병합 후 `main` 이력에 없다. 병합 후 `main` 해시로 후속 PR을 낼지, 브랜치 해시를 그대로 공개할지 정해야 한다.
- **7.3과 게이트의 순서:** 7.3은 커밋 뒤에만 끝나므로, 7.3만 남았을 때 게이트를 어떻게 통과시킬지 정해야 한다.
- **공개 쇼케이스 진입점:** `/showcase/controlled-ai`는 어디에서도 링크하지 않는다. 스펙 요구는 아니며, 포트폴리오에서 직접 URL로 연다면 그대로 둬도 된다.

## 확정된 결정

2026-11-02에 사용자가 Controlled AI(Flow·Cost·Quality·Risk) 설계의 권장안을 승인했다. 설계서는 https://claude.ai/artifact/2oMqonx9WPBYJaxoPXhgRX 이다.

- 구현은 Step 1(추적·비용 회계)부터 Step별 OpenSpec change 하나로 진행한다. 새 통제는 `off → shadow → enforce` 플래그로 도입한다.
- Ask 수리: 스트리밍을 유지하고 사후에 한 번 수리해 `citations.text`로 교체한다 (Step 3).
- 검증된 위키 페이지 덮어쓰기: 승인 보류이지만 shadow로 빈도를 확인한 뒤 적용한다 (Step 4).
- 공개 포트폴리오는 합성 증거 파일만 쓰고 운영 DB에 연결하지 않는다.
- 그래프 채널은 off를 유지하며, 운영은 4채널이 맞다.
- Langfuse는 Cloud Hobby(JP 권장)를 개발자 전용으로 쓰고 본문은 보내지 않는다. 예산과 Control Room의 원천은 Postgres다.
- 사용자는 모든 작업을 나중에 확인할 화면을 원한다. 각 Step은 Control Room 탭 하나를 실제 데이터로 채워야 한다.

## 이미 아는 실패

- `test_cross_tenant_ingest_is_forbidden_with_a_fixed_body[file]`: 기준 커밋에서도 403 대신 502를 받는다. 업로드는 차단되지만 응답 코드가 틀리다. 로컬 Storage v1.44.11이 RLS 거부(`42501`)를 HTTP 400과 `code` 없는 본문으로 돌려주어 `apps/api/src/api/storage.py`의 `_error_code`가 권한 거부로 인식하지 못한다. Windows에서 `supabase@2.84.2`로 띄운 구버전 이미지 때문일 수 있으나 확인하지 않았다. Mac에서 더 새로운 Storage 이미지로 다시 확인하고, 재현되면 별도 수정으로 다룬다. 운영 Storage의 응답은 확인하지 않았다.
- `apps/worker/tests/test_transcript.py`: Windows의 venv에 `youtube_transcript_api`가 없어 수집 오류가 났다. Mac에서 `uv sync` 뒤 다시 확인한다.
- 대시보드 전체 테스트: 기본 5초 제한에서 부하로 10건 안팎이 시간 초과로 실패했고, 실패하는 테스트는 실행마다 달랐다. `vitest run --testTimeout=30000`에서는 462건이 모두 통과했다.
- `next build`: `next/font` 로더의 파싱 오류로 한 번 실패했고 재시도에서 통과했다. Google Fonts 응답 때문으로 보이며, `app/layout.tsx`는 이번 변경 범위가 아니다.
- `test_tenant_isolation_full_path.py`: **간헐적으로 실패하며 원인을 모른다.** 한 번은 다른 무거운 작업과 동시에 돌 때 `ReadTimeout`이 났고, 격리 리뷰어의 실행에서는 `test_requester_jwt_delete_matrix_blocks_both_foreign_directions[raw_sources]` 1건이 ERROR였다. 같은 파일의 단독 실행(32건)과 전체 pytest에서는 통과했다. 부하 탓이라고 증명하지 못했으므로 Mac에서 여러 번 돌려 확인한다.

## 환경에서 알아둘 점

- 저장소에 들어 있지 않으므로 Mac에서 직접 준비할 것: `.env`, 로컬 Supabase 데이터, `.venv`, `node_modules`.
- 준비 순서는 `uv sync`, `apps/dashboard`에서 `pnpm install`, 로컬 Supabase 시작이다. 로컬 포트는 544xx 고정이다.
- 마이그레이션은 0026까지 로컬에 적용해야 한다. `supabase/tests/0023_job_trace.sql`로 검증할 수 있다.
- `apps/worker/tests/test_controlled_ai_evidence.py`의 사용법에 있는 `PYTHONPATH` 구분자는 Windows 기준(`;`)이다. Mac에서는 `:`를 쓴다.
- 대시보드의 한 파일만 돌릴 때는 `./node_modules/.bin/vitest run tests/X.test.tsx`를 쓴다. `pnpm test -- X`는 필터가 먹지 않고 전체를 돈다.
- `service_role`은 `ask_messages`를 조회할 수 없다. 테스트에서는 작성자 JWT로 읽는다.
- 누출 검사 표식은 ASCII여야 한다. 한글은 JSON 직렬화와 콘솔 인코딩에서 형태가 바뀌어 유출되어도 검사를 통과한다.
- `docs/ref/ref0.png`, `docs/ref/ref2.png` 삭제와 `skills-lock.json`은 이 change와 무관해 커밋에서 제외했다. Windows 작업 트리에 그대로 남아 있다.

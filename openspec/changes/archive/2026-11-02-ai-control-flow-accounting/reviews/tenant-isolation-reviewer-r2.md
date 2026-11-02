# Tenant Isolation 리뷰 — ai-control-flow-accounting r2

- 판정: **needs_fix**
- 대상: `git diff 79b68fe` + 추적되지 않은 파일 (HEAD = `66a2afd`, 1라운드 조치는 미커밋 작업 트리)
- 일시: 2026-11-02T10:16:44Z

## 요약

r1의 치명 지적(다른 테넌트의 `usage_events`에 비용 기록)은 실제 스택에서 재현되지 않는다. 테넌트 경계를 넘는 경로는 이번 라운드에서 찾지 못했다. 다만 새 내보내기 라우트의 "본문이 실릴 수 없다"는 약속이 거짓이고, 스트림 전 실패 로그의 분류 값이 운영 설정에서 지워지며, design과 #170의 "월 상한에 영향이 없다"가 실측과 다르다. 코드 수정과 문서 정정으로 끝나는 항목이라 `needs_fix`다.

## 검사 결과

| # | 항목 | 결과 | 근거 |
| --- | --- | --- | --- |
| A-1 | 사용자 경로의 service_role | 통과 | `apps/api/src`에 `service_client`, Langfuse, `observability` 사용 없음. 주석에만 등장 |
| A-2 | 신규 테이블 RLS 동시 활성화 | 해당 없음 | 신규 테이블 없음 |
| A-3 | `anon` 신규 GRANT·정책 | 통과 | `start_ask_turn`, `finalize_ask_turn`, `ask_trace_aggregate`의 `proacl`에 anon 없음. `ask_messages`의 anon 권한은 기존 `REFERENCES`, `TRIGGER`, `TRUNCATE`뿐. anon 키를 Bearer로 쓰면 인증이 필요한 전 라우트에서 403 또는 본문 검증 422 |
| A-4 | service_role 코드의 `workspace_id` | 통과 | `/retrieval`과 `/ask` 모두 게이트 뒤에만 워커를 부른다(실측). 임베딩을 부르는 라우트는 이 둘뿐. 내보내기 라우트의 임의 `workspace_id`는 DB에 닿지 않는다 |
| A-5 | 자식 테이블 복합 FK | 해당 없음 | 신규 자식 테이블 없음 |
| B-6 | 0행 → 403 | 통과 | `/retrieval` 게이트와 `get_trace` 모두 `WorkspaceForbidden`. 실제 호출에서 403 |
| B-7 | 42501 → 403 | 통과 | 401 판정보다 먼저 평가(`errors.py:245`, `:252`). 비멤버 `/ask` 42501 → 403 실측 |
| C-8 | 핸들러 재실행 안전성 | 통과 | upsert 키 변경 없음. 기록 순서 변경은 호출당 한 행을 유지한다. 아래 표 참고 |
| C-9 | `jobs` 직접 UPDATE 금지 | 통과 | 이번 조치의 `queue.py` 변경은 주석뿐 |
| D-10 | `hnsw.iterative_scan` | 해당 없음 | 벡터 RPC 변경 없음 |
| D-11 | 토크나이저 일치 | 해당 없음 | 변경 없음 |
| D-12 | `search_tsv` 생성 컬럼화 | 해당 없음 | 시도 없음 |
| D-13 | 프롬프트 `str.format` | 통과 | 이번 조치 파일에 없음 |
| D-14 | 인용 앵커 | 통과 | 컨텍스트 조립 변경 없음 |
| E-15 | 마이그레이션 번호 | 통과 | 최대 `0026`. 번호를 늘리지 않은 파일 수정은 클라우드 미적용이라는 전제에서 순서 규칙에 걸리지 않는다. 클라우드 상태 자체는 이번에 확인하지 않았다 |

## r1 지적 해소 여부

| r1 | 내용 | 결과 | 근거 |
| --- | --- | --- | --- |
| 1 | `/retrieval` 교차 테넌트 비용 기록 | **해소** | 아래 재현 1 |
| 2 | `total_ms` 범위 초과로 집계 500 | 해소 | `1e20`, `-1`, `"abc"`, 객체 모두 집계 200이고 `p50`에서 제외. `3000`만 반영 |
| 3 | API의 Langfuse 키 | 해소 | `ApiSettings`와 API 소스에서 제거. 새 표면의 문제는 지적 1 |
| 4 | `bootstrap` 귀속 | 해소 | `bootstrap` 바인딩 뒤 헤더 없음과 형식 오류 모두 200, 행 증가 0, `worker.query_embedding_usage_unattributed` 경고 |
| 5 | `trace_id` 변경 | 해소 | `trace_id`, `question`, `workspace_id`, `client_turn_id`, `created_at` PATCH 전부 403(42501). 수용한 잔여 위험의 근거는 지적 4 |
| 6 | 종료 시 사용량 유실 | **부분 해소** | 드레인과 경고는 동작한다. 진행 중 스트림이 있으면 드레인에 닿지 못한다. 지적 7 |
| 7 | 전송 실패 표시 | 해소 | docstring과 체크리스트 반영 |
| 8 | `succeeded` 오표시 | 해소 | 주석 수정과 Risks 기록 |
| 9 | `p_since` 분리 | 해소 | 같은 날의 `00:00:01`과 `23:59:59` 결과 동일. 잔여 사항은 지적 9 |
| 10 | 사소한 불일치 | 해소 | `control.py` 주석 수정, `export_ask_turn` 필드 추출이 `try` 안으로 이동 |

## 요청 지점별 결과

| 지점 | 결과 | 근거 |
| --- | --- | --- |
| 내부 라우트 인증 순서 | 통과 | 토큰 없음+유효 본문 401, 토큰 없음+추가 필드 또는 깨진 JSON 422. 어느 경우도 span 0건. 본문 검증이 먼저지만 내보내기 부작용은 없고 기존 내부 라우트와 같은 형태다 |
| 허용 필드와 본문 차단 | **위반** | 지적 1 |
| 토큰 재사용 | 수용 가능 | 새로 생기는 능력은 Langfuse 쓰기뿐이다. 읽기와 삭제, DB 접근은 없다. 같은 토큰은 이미 `/internal/llm-chat`으로 임의 워크스페이스에 비용을 쓸 수 있으므로 위험 범위가 크게 늘지 않는다 |
| 임의 `workspace_id`와 보고서 | 영향 한정 | 해시와 메타데이터만 나간다. DB 행 0. `X-Trace-Id`도 신뢰하므로 임의 Langfuse trace에 섞을 수 있으나 개발자용 사본에 한정된다 |
| `HttpAskTurnExporter`의 로그 | 통과 | 예외 문구에 토큰을 넣은 재현에서도 `error_type=ConnectError`만 남음. 거부는 `status_code`만 남음 |
| `HttpAskTurnExporter`의 예외 삼킴 | 일부 지적 | 지적 8 |
| 분리 태스크의 수명 | 일부 지적 | 강한 참조와 2초 제한은 있다. API 종료 시 드레인은 없다. 지적 8 |
| 401이 존재를 드러내는가 | 통과 | 전 라우트 매트릭스에서 위조 토큰은 실재와 부재 대상에 같은 응답(401, 또는 본문 검증 422) |
| 42501이 401로 내려가는가 | 통과 | 판정 순서와 `test_db_error_mapping.py`. PostgREST가 anon 42501을 401로 줘도 403 |
| 401 매핑 범위 | 일부 지적 | 지적 6 |
| `fail_preparation`의 403 계약 | 통과 | 게이트(`routers/ask.py:129`)는 응답 시작 전에 있어 403과 401이 유지된다. 그 뒤의 실패는 기준 커밋에서도 상태 코드를 바꿀 수 없었다 |
| `fail_preparation`의 격리 위반 처리 | 수용 가능, 일부 지적 | 게이트 통과 뒤 42501과 `WorkspaceForbidden`은 HTTP 200의 `retrieval_unavailable` 오류 턴이 된다. 자료는 나가지 않는다. 진단 신호가 약한 것은 지적 5 |
| `fail_preparation`의 로그 내용 | 통과 | 질문과 예외 문구에 넣은 표식이 로그와 저장값에 없음. `error_type`만 남음 |
| `CancelledError` 삼킴 | 통과 | `except Exception`이 잡지 않는다. 끊김 처리는 지적 3 |
| `llm.py`, `embedding.py` 기록 순서 | 통과 | 공급자 응답 하나당 한 행이고, 재시도는 새 호출이라 새 행이 실제 청구와 맞다. 기록 실패는 기존처럼 예외로 올라간다. `empty_choices`, `missing_content` 분류 유지. `on_usage`는 입력이 비면 불리지 않음 |
| `finalize_ask_turn`과 컬럼 권한 | 통과 | 실제 API 경로로 턴이 `no-evidence`로 종결됨. 마이그레이션의 `ask_messages` UPDATE는 `0025:173` 하나가 현재 정의이고 네 컬럼만 쓴다. API와 워커 소스에 직접 UPDATE 없음 |
| SIGTERM 예산 | 일부 지적 | 스트림이 없으면 최악 25초(`max(20, 리스너+2) + 3`)로 30초 안이다. 스트림이 있으면 지적 7 |
| 집계 함수 권한 | 통과 | viewer와 비멤버 직접 호출 모두 403(42501) |

### 재현 1: r1 치명 지적

API는 실제 앱, DB는 실제 PostgREST, 워커는 실제 `/internal/query-embedding` 라우트와 `_QueryUsageSink`의 service_role 쓰기를 썼고 공급자만 스텁했다. 호출자가 돌린 회귀 테스트와 달리 임베딩 경계를 주입하지 않았다.

| `POST /workspaces/{피해자}/retrieval` | 응답 | 공급자 호출 | 피해자 `usage_events` |
| --- | --- | --- | --- |
| 비멤버 JWT | 403 `forbidden` | 0 | 0 |
| `Bearer not-a-jwt` | 401 `unauthorized` (PGRST301) | 0 | 0 |
| 다른 키로 서명한 JWT | 401 (PGRST301) | 0 | 0 |
| 만료 JWT | 401 (PGRST303) | 0 | 0 |
| anon 키 | 403 | 0 | 0 |
| viewer 대조군 | 200 | 1 | 1 (`embedding`, `query_embedding`) |

부재 UUID에서도 비멤버 403, 위조 401로 같다. `/ask`도 비멤버 403, 위조 401에 공급자 호출 0이다.

## 조치가 필요한 항목

1. **내부 내보내기 라우트가 본문을 막지 못한다** (심각도: 보통)
   - 위치: `apps/worker/src/worker/ask_turn_export.py:9`, `:30`, `packages/core/src/nexuswiki_core/observability.py:204`, `:319-332`
   - 깨지는 것: 파일 머리말은 본문 차단이 호출자의 조립에 기대지 않는다고 하지만, `control_report`는 `dict[str, Any]`이고 추출 뒤의 값에 타입 제한이 없다. `_mask`는 값 길이만 보고 키는 보지 않는다.
   - 재현(토큰 보유, 실제 SDK와 메모리 exporter): `spans[0].name`에 4,000자 표식을 넣자 `langfuse.observation.metadata.span_BODYLEAK...` 4,046자 키가 그대로 도달했다. `route.decision` 120자, `route.reason`과 `policy_version`의 자유 문장, `citation.cited_anchor_count`의 문자열, `total_ms`의 중첩 객체도 도달했다. 128자 초과 값과 `question` 키는 마스킹됐다.
   - 범위: 토큰이 있어야 하고 현재 API의 조립은 고정 이름과 숫자만 싣는다. 지금 고객 본문이 나가는 경로는 아니다. 그러나 이 검사는 API 쪽 실수를 막으려고 있는 방어선이고, 고객 원문을 외부로 복제하지 않는 경계다.
   - 조치: 라우트 또는 `export_ask_turn`에서 구조를 닫는다. `spans[].name`은 `retrieval`, `context`, `llm_stream`, `citation`만, `route.decision`은 `AskRoute` 값만, 수치 필드는 숫자만 허용한다. 위반하면 그 필드나 보고서를 버린다. `_mask`에도 키 길이 검사를 더한다. 긴 span 이름과 자유 문장 사례를 회귀 테스트에 넣는다.

2. **"월 상한에 영향이 없다"가 실측과 다르다** (심각도: 보통)
   - 위치: `openspec/changes/ai-control-flow-accounting/design.md:168`, 이슈 #170 본문, `apps/worker/src/worker/llm_stream.py:146-153`, `apps/worker/src/worker/llm.py`의 `cost_micros`
   - 깨지는 것: design:163은 "중단된 스트림의 실제 비용이 0으로 기록될 수 있다"고 하는데, design:168과 #170은 같은 상황을 상한에 영향이 없다고 적었다. 사용량 프레임은 스트림 끝에 온다. 그 전에 끊으면 `incomplete` 행의 비용은 0이고 상한 합계는 늘지 않는다.
   - 재현(실제 uvicorn 리스너, 스트림 스텁): 첫 델타 뒤 연결을 끊자 `record_usage`에 `usage={}`, `incomplete=True`가 전달됐다. 완주한 호출에서는 같은 스텁의 비용 0.5달러가 전달됐다. `cost_micros({})`는 0이다.
   - 결과: 멤버가 답을 받고 마지막 프레임 전에 끊기를 반복하면 Ask 비용이 상한에 쌓이지 않는다. 탭을 닫는 정상 사용도 같은 방향으로 과소 집계한다. 테넌트 경계는 넘지 않으며 피해는 운영자의 공급자 비용이다. 공급자가 중단된 스트림을 얼마나 청구하는지는 실제로 호출해 확인하지 않았다.
   - 조치: design:168과 #170의 문구를 "건수는 남지만 금액은 과소 집계되고 상한이 늦게 걸린다"로 고친다. #170 또는 별도 이슈에 사후 대조나 입력 크기 기반 추정 차감을 범위로 넣는다.

3. **#170의 범위가 실제 끊김 구간보다 좁다** (심각도: 낮음)
   - 위치: `apps/api/src/api/services/ask.py:677-686`, `:722-750`, `openspec/changes/ai-control-flow-accounting/specs/grounded-answering/spec.md:4`, 이슈 #170
   - 판단: 분리 자체는 타당하다. 기준 커밋에도 있는 동작이고 취소 안에서 DB에 쓰는 설계가 따로 필요하다.
   - 깨지는 것: #170과 스펙 문장은 "델타를 받는 도중"을 말한다. uvicorn 0.52의 `spec_version`이 2.3이라 Starlette는 끊김을 감지하면 생성기를 취소하므로, 응답 시작 뒤의 모든 `await`가 해당한다.
   - 재현(실제 uvicorn과 PostgREST): 검색 대기 중 델타 0건에서 끊자 턴은 `streaming`, `control_report`는 null, 내보내기 0회였다. 답변을 다 받고 `finalize_ask_turn` 중에 끊는 경우도 같은 구조다(이 경우는 코드 판독).
   - 조치: #170의 Given을 "응답을 시작한 뒤 어느 구간이든"으로 넓히고 스펙 문장도 맞춘다. 같은 이슈에서 `_finalize_turn`이 `httpx` 전송 실패를 잡지 않는 경로(`ask.py:582`)도 다룬다. `ReadTimeout`에서 예외가 스트림 밖으로 나가 `done`도 내보내기도 없음을 재현했다.

4. **`p_trace_id` 수용 논증의 전제가 사실이 아니다** (심각도: 낮음)
   - 위치: `openspec/changes/ai-control-flow-accounting/design.md:167`, 대비 `:164`
   - 깨지는 것: "작성자는 RLS 때문에 다른 멤버의 trace 존재를 판정할 수 없고, definer로 확인하면 오히려 존재 탐지 경로가 생긴다"는 틀렸다. design:164가 적었듯 멤버는 `usage_events.trace_id`를 읽는다. 탐지 경로는 이미 있으므로 이 문장은 거부 검사를 하지 않을 근거가 되지 못한다.
   - 재현(viewer, 실제 API): `usage_events`에서 다른 멤버의 trace를 200으로 읽음 → 수집 trace 상세 403 → `start_ask_turn`에 그 trace를 넣어 직접 호출 200 → 같은 상세가 200으로 `calls` 반환 → 같은 `client_turn_id`로 `/ask` 재전달 → 내 임베딩 행이 그 trace에 묶이고 응답 `X-Trace-Id`도 그 값이다.
   - 결론은 유지된다: 돌아온 `calls`는 그 viewer가 RLS로 직접 읽을 수 있는 값이고, Ask 경로는 `jobs`를 읽지 않으며(`control.py:332-333`), 예산 합계는 실제 사용량만 더한다.
   - 빠진 내용: 스펙의 "다른 멤버의 Ask trace 요청은 403" 시나리오와 viewer의 수집 trace 비표시가 이 경로에서는 성립하지 않는다. 같은 일을 직접 `INSERT`로도 할 수 있다(지적 9). "다른 테넌트의 trace는 묶이지 않는다"는 Postgres에서만 참이다. Langfuse trace ID는 `workspace_id` 없이 trace 값만으로 만들어지므로(`observability.py:296`), 상대 trace를 아는 사용자는 개발자용 사본에서 두 테넌트의 관측을 섞을 수 있다.
   - 조치: Risks 항목에서 거짓 전제를 지우고 위 세 사실을 적어 수용 근거를 "새로 노출되는 값이 없다"로 바꾼다. 코드 변경은 요구하지 않는다.

5. **스트림 전 실패의 분류가 운영 로그에서 지워진다** (심각도: 낮음)
   - 위치: `apps/api/src/api/services/ask.py:655`
   - 깨지는 것: 키 이름이 `token`인데 `token`은 `REDACTED_KEYS`에 있다. 운영 로그 구성으로 실행하자 `"token":"[REDACTED]"`로 나왔다. `retrieval_unavailable`과 `context_unavailable`을 로그에서 구별할 수 없다. 넓은 `except Exception`이라 코드 결함, 권한 회귀(42501), JWT 만료가 모두 경고 수준의 클래스 이름 하나로 뭉쳐 전부 "검색 불가"로 보인다.
   - 비밀과 본문은 실리지 않는다. 이 지적은 진단 신호의 문제다.
   - 조치: 키를 `error_token`으로 바꾼다. `DatabaseError`이면 `sqlstate`를 더하고, 예상한 외부 실패가 아닌 예외는 `error` 수준으로 남긴다.

6. **401 매핑이 넓으면서도 전 라우트에 닿지 않는다** (심각도: 낮음)
   - 위치: `apps/api/src/api/errors.py:252`, `apps/api/src/api/routers/sources.py:570-573`
   - 깨지는 것 (가): 상태 코드만 본다. PostgREST가 내는 JWT 거부는 실측상 `PGRST301`, `PGRST303`인데, 게이트웨이의 다른 401도 `db.jwt_rejected` 경고와 401이 된다. 예를 들어 클라우드에서 잘못된 publishable key가 그런 응답을 낸다면 서버 설정 사고가 전 사용자의 재로그인 요구로 보이고 500 경보도 울리지 않는다. 로컬 게이트웨이는 잘못된 `apikey`를 거부하지 않아 재현하지 못했고, 클라우드 동작은 확인하지 않았다.
   - 깨지는 것 (나): design의 "전 라우트에서 401"이 `POST /sources/youtube-videos`에는 성립하지 않는다. `not-a-jwt`로 호출하면 `202`와 `{"status":"failed","reason":"internal"}`이 돌아오고 `error` 로그가 남는다. 행은 만들어지지 않는다. 42501만 다시 올리는 분기가 401을 영상별 실패로 접는다.
   - 조치: 판정을 `PGRST30x` 코드로 좁히고 나머지 401은 500으로 둔다. `sources.py`에서 `error.status_code == 401`도 다시 올린다. 두 사례를 `test_db_error_mapping.py`에 더한다.

7. **진행 중 스트림이 있으면 드레인과 flush에 닿지 못한다** (심각도: 낮음)
   - 위치: `apps/worker/src/worker/__main__.py:283-288`, `apps/worker/src/worker/llm_stream.py:168-171`, `apps/worker/src/worker/queue.py:58`
   - 깨지는 것: `uvicorn.Config`에 `timeout_graceful_shutdown`이 없어 `await server_task`가 스트림 끝까지 기다린다. API의 스트림 제한은 130초(`LLM_STREAM_TIMEOUT_SECONDS`)이고 플랫폼 유예는 30초다. 그 사이 SIGKILL을 맞으면 `_drain_usage_writes`와 `flush_observability`가 실행되지 않고, r1이 지적한 대로 기록도 로그도 없이 사라진다. 잡 반납은 별도 태스크라 영향이 없다.
   - 재현: 약 6초 남은 스트림을 두고 `stop`을 세우자 리스너가 5.8초 뒤에 끝났다. 2초 드레인 예산은 이 대기 뒤에 시작된다. 드레인 자체는 제한 0.3초에 정확히 끝나고 `worker.usage_writes_abandoned`를 남겼다.
   - 함께 볼 것: `LlmStreamService._pending_records`는 드레인 대상이 아니다. 끊긴 호출의 기록이 `shield`로 분리된 채 종료와 겹치면 같은 방식으로 사라진다(코드 판독, 창은 INSERT 한 건 길이).
   - 조치: 유예 안의 `timeout_graceful_shutdown`을 주고 `_pending_records`도 드레인에 포함한다. 강제 종료된 스트림이 `incomplete`로 남는지 테스트한다.

8. **`HttpAskTurnExporter`가 `httpx.HTTPError`만 잡는다** (심각도: 낮음)
   - 위치: `apps/api/src/api/services/ask.py:179`, `apps/api/src/api/main.py:44`
   - 깨지는 것: 닫힌 클라이언트의 `RuntimeError`와 직렬화 실패의 `ValueError`가 태스크 밖으로 빠져 `Task exception was never retrieved`만 남고 `ask.turn_export_failed`는 나오지 않는다. 둘 다 재현했다. 문구에 비밀은 없고 답변에 영향도 없다. NaN은 현재 조립으로 도달하지 않으며, 닫힌 클라이언트는 종료 경합에서만 생긴다. 종료 때 남은 태스크를 기다리지 않아 배포마다 몇 건은 사라질 수 있다.
   - 조치: `except Exception`으로 넓혀 `error_type`만 남긴다. 드레인은 개발자용 사본이므로 수용해도 된다. 수용한다면 Risks에 적는다.

9. **집계의 건수도 작성자가 위조할 수 있는데 설명에 빠져 있다** (심각도: 낮음)
   - 위치: `supabase/migrations/0018_ask_history.sql:127`, `supabase/migrations/0026_ask_trace_aggregate.sql:101`
   - 깨지는 것: 함수 설명은 결정 분포와 지연만 참고 수치라고 한다. `authenticated`는 전 컬럼 INSERT 권한이 있어 작성자가 `status`, `trace_id`, `created_at`, `control_report`를 고른 턴을 직접 넣을 수 있다. `status`는 UPDATE로도 바꿀 수 있다.
   - 재현: viewer가 `created_at=2099-01-01`, `status=resolved`로 직접 INSERT해 201을 받았고, owner의 집계에서 다음 날 시작 창에도 그 행이 잡혔다. 미래 시각이라 어느 창에서도 빠지지 않는다. 다른 멤버의 행은 건드리지 못하고 비용 합계도 변하지 않는다.
   - 잔여: `p_since` 내림은 과거 창 조작만 막는다. editor가 집계를 짧은 간격으로 반복 호출해 차이를 보면 새 턴 하나의 상태, 결정, 지연을 얻을 수 있다(코드 판독). 시각과 비용은 이미 `usage_events`로 보이므로 새로 드러나는 값은 상태, 결정, 지연이다.
   - 조치: INSERT를 `start_ask_turn`에 필요한 컬럼으로 좁히면 `created_at`과 `control_report` 위조가 막힌다. `0025`를 아직 고칠 수 있으므로 지금이 비용이 가장 작다. 좁히지 않으면 함수 설명과 Risks를 "건수도 참고 수치"로 고치고 폴링 잔여를 함께 적는다.

## 판정 근거

테넌트 경계를 넘거나 데이터를 조용히 손상하는 경로를 찾지 못했으므로 `blocked`가 아니다. A-1, A-3, A-4는 모두 통과했고 r1의 치명 지적은 실제 워커 경로에서 재현되지 않는다. 그래도 `pass`는 아니다. 지적 1은 이번에 새로 만든 외부 전송 경계의 약속이 실측으로 깨졌고, 지적 2는 사람이 위임한 결정의 근거 문장이 사실과 다르다. 지적 5와 6, 7도 작은 코드 수정으로 끝난다. 3라운드가 마지막이므로 지적 1, 2, 4, 5를 우선 처리하고, 3, 6~9는 고치거나 수용 사실을 design에 남기는 것으로 정리하면 된다.

## 검증 범위

- 재현 스크립트(저장소 밖): 실제 API 앱과 PostgREST, 실제 워커 라우트와 service_role 쓰기, 실제 uvicorn. 공급자와 Ask 스트림만 스텁. 재현 데이터를 정리했고 마지막 확인에서 `test-%` 사용자와 워크스페이스 모두 0건이다.
- 실행한 테스트: `test_db_error_mapping.py`, `/retrieval` 격리 3건, `test_control_router.py` 합계 23 passed. `test_ask_turn_export.py`, `test_query_embedding.py`, `test_worker_main.py` 합계 27 passed. `supabase/tests/0023_job_trace.sql` ok.
- 실행하지 않음: 전체 스위트, 클라우드 환경, 실제 공급자, 실제 Langfuse 서버, 마이그레이션 처음부터 재적용. 현재 함수와 권한의 동작만 실측했고 수정된 파일을 빈 DB에 적용해 보지는 않았다. 클라우드 push 전 재적용 확인이 필요하다.
- r1의 간헐 실패: 이번에는 격리 스위트 전체를 돌리지 않았다. 호출자의 3회 통과는 재현되지 않았다는 사실일 뿐이며 원인은 여전히 모른다. 스펙 리뷰어와 같은 스택을 동시에 쓰는 동안 `test-%` 행 수가 변하는 것은 관측했지만, 이것이 원인이라는 증거는 아니다.

## 범위 밖 참고

- `authenticated`에 `ask_messages`, `ask_threads`의 `TRUNCATE`, `TRIGGER`, `REFERENCES`가 남아 있다. r1에서 적은 대로 이번 변경에서 생긴 것이 아니고 PostgREST로 도달할 수 없다. 다만 `0025`가 `ask_messages` 권한을 다루는 김에 함께 회수할 수 있다.
- `.env.local` 읽기는 권한 설정으로 거부됐고, 이 리뷰에는 필요하지 않아 다시 시도하지 않았다.

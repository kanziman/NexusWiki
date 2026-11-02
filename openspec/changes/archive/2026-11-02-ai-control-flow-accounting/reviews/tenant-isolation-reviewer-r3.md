# Tenant Isolation 리뷰 — ai-control-flow-accounting r3

- 판정: **needs_fix**
- 대상: `git diff 79b68fe` + 추적되지 않은 파일 (HEAD = `66a2afd`, r1·r2 조치는 미커밋 작업 트리)
- 일시: 2026-11-02T10:39:56Z

## 요약

테넌트 경계를 넘는 경로는 이번에도 찾지 못했다. r2의 코드 지적은 전부 해소됐고 불변 규칙 위반도 없다.

`pass`가 아닌 이유는 수용 기록 두 건이 재현 결과와 다르기 때문이다.

1. `start_ask_turn`의 새 검사를 **직접 INSERT로 우회**할 수 있다. 스펙 시나리오와 `0025`의 ⚠️ 주석, design Risks는 이 경로가 막힌 것처럼 적었다.
2. design Risks 첫 줄의 **"예산 판정은 영향받지 않는다"** 가 r2 지적 2와 같은 이유로 거짓이다.

둘 다 새로 드러나는 값이 없고 문서 정정만으로도 해소된다. 3라운드 규칙상 호출자가 `blocked`로 확정해 사람에게 넘기는 경우에 해당한다. 이 `needs_fix`는 격리 사고가 아니라 기록과 사실의 불일치를 뜻한다.

## 검사 결과

| # | 항목 | 결과 | 근거 |
| --- | --- | --- | --- |
| A-1 | 사용자 경로의 service_role | 통과 | `apps/api/src`에 `service_client`, `LANGFUSE`, `nexuswiki_core.observability` 사용 없음. 주석 3곳에만 단어가 등장 |
| A-2 | 신규 테이블 RLS 동시 활성화 | 해당 없음 | 신규 테이블 없음 |
| A-3 | `anon` 신규 GRANT·정책 | 통과 | `start_ask_turn`, `finalize_ask_turn`, `ask_trace_aggregate`의 `proacl`에 anon 없음. `jobs`, `usage_events` 정책은 `authenticated` 전용. 영상 등록 anon 키 403 실측 |
| A-4 | service_role 코드의 `workspace_id` | 통과 | r2 뒤에 바뀐 워커 파일은 `__main__.py`, `ask_turn_export.py`, `llm_stream.py`뿐이고 새 DB 접근이 없다. 내보내기 라우트의 `workspace_id`는 해시로만 나간다 |
| A-5 | 자식 테이블 복합 FK | 해당 없음 | 신규 자식 테이블 없음 |
| B-6 | 0행 → 403 | 통과 | 통제실 상세의 0행 경로 403 실측(`control.py:386`) |
| B-7 | 42501 → 403 | 통과 | 새 검사의 42501이 PostgREST 403으로 반환됨. 비멤버 `/ask` 403 실측. 판정 순서는 `errors.py:261`이 JWT 판정보다 앞 |
| C-8 | 핸들러 재실행 안전성 | 통과 | upsert 키 변경 없음. 재전달은 새 검사보다 먼저 돌아가고 `done`까지 정상 |
| C-9 | `jobs` 직접 UPDATE 금지 | 통과 | 추가된 코드에 직접 쓰기 없음 |
| D-10 | `hnsw.iterative_scan` | 해당 없음 | 벡터 RPC 변경 없음 |
| D-11 | 토크나이저 일치 | 해당 없음 | 변경 없음 |
| D-12 | `search_tsv` 생성 컬럼화 | 해당 없음 | 시도 없음 |
| D-13 | 프롬프트 `str.format` | 통과 | 추가된 코드에 없음 |
| D-14 | 인용 앵커 | 통과 | `_context_blocks` 호출이 `try` 안으로 옮겨졌을 뿐 내용 변경 없음 |
| E-15 | 마이그레이션 번호 | 통과 | 최대 `0026`, 번호 추가 없음. 클라우드 미적용은 기록(`migration-0023-0026-record.md`)과 호출자 전제에 따른 것이고 이번에 직접 확인하지 않았다 |

## r2 지적 해소 여부

| r2 | 조치 | 결과 | 근거 |
| --- | --- | --- | --- |
| 1 | 내보내기 값 닫기 | **해소** | `r2_export.py` 재실행. 키와 값의 본문 표식 도달 False, 형태 오류 4종 모두 204. 실제 값(`hybrid-rrf-v1`, `default`, `exact_title_match`, `{kind}_only`, 구간 이름 4개)은 모두 패턴을 통과해 정상 값이 지워지지 않는다. 잔여는 참고 1 |
| 2 | 월 상한 문구 | **부분 해소** | `design.md:169`와 #170 본문은 정확하다. 같은 내용을 반대로 적은 `design.md:161`이 남았다. 지적 2 |
| 3 | 범위 | 해소 | 스펙은 "before the turn ends"로 넓어졌고, 전송 실패 재현에서 이벤트가 `['meta','citations']`로 끝나고 예외가 밖으로 나가지 않는다. #170의 표현 차이는 참고 3 |
| 4 | 새 trace 검사 | **코드는 설명대로 동작하나 기록이 틀림** | 지적 1 |
| 5 | 로그 키 | 해소 | 운영 로그 구성에서 `"failure":"retrieval_unavailable"`이 그대로 남는다(`ask.py:685`) |
| 6 | 401 판정 | 해소, 기록 권고 | 영상 등록 위조 토큰 401, anon 키 403. 전 라우트 매트릭스에서 실재와 부재가 같다. 게이트웨이 설명은 참고 2 |
| 7 | 리스너 종료 | 해소 | 아래 재현 3. 호출자 실측과 일치한다 |
| 8 | 내보내기 예외와 드레인 | 해소 | 닫힌 클라이언트와 NaN 모두 처리되지 않은 예외 0건(`ask.py:179`). 드레인은 `main.py:46`에서 클라이언트를 닫기 전에 실행된다 |
| 9 | 집계 건수 위조 | 해소 | `design.md:170`, `0026:101`에 수용 사실이 적혔고 화면도 "참고 수치"로 표시한다. 내용이 실측과 맞다 |

## 요청 지점 4의 결과: `start_ask_turn` 새 검사

| 지점 | 결과 | 근거 |
| --- | --- | --- |
| 존재 탐지 | **새 경로 아님** | security invoker라 RLS를 받는다. 비멤버는 실재와 부재 trace에서 응답 본문까지 동일하다(`ask_threads` RLS 42501). 멤버는 어차피 `jobs`와 `usage_events`를 직접 읽는다 |
| 정상 경로 | **막지 않음** | 실제 `/ask`로 새 턴 200, 사용량이 쌓인 뒤의 재전달 200에 같은 trace와 `done`, 다른 턴 200에 다른 trace, `p_trace_id` null 200. API는 인입 헤더를 믿지 않으므로(`trace.py:152`) 클라이언트가 검사를 건드릴 수 없다 |
| 재전달 | 통과 | 거부될 값을 넣어도 기존 턴과 저장된 trace를 돌려준다. `0025:91-97`이 검사보다 먼저다 |
| 잠금 | 합당 | 기존 advisory 잠금 안에서 읽기만 한다. 행 잠금을 추가하지 않는다. 동시 호출 경합은 값을 미리 알 수 없어 실익이 없다 |
| 인덱스 | 합당 | `authenticated` 역할과 `force_generic_plan`, 사용량 6만 행과 잡 2만 행에서 두 조회 모두 Index Only Scan이다. 부분 인덱스 조건을 만족한다. 실행 0.015ms, 0.011ms. 함수 5회 5.2ms |
| 아직 행이 없는 trace | design과 일치 | 다른 멤버의 `ask_messages`에만 있는 값을 넣으면 200이지만 값을 얻을 경로가 없다. 받는 것도 자기 행뿐이다 |
| `ask_messages` 직접 INSERT | **design과 불일치** | 지적 1 |

## 조치가 필요한 항목

1. **이미 쓰인 trace로 턴을 만드는 일이 직접 INSERT로 여전히 된다** (심각도: 보통)
   - 위치: `openspec/changes/ai-control-flow-accounting/specs/ai-control-room/spec.md:63-65`, `design.md:164`, `:167`, `supabase/migrations/0025_ask_trace.sql:99-103`, `apps/api/tests/test_control_router.py:459-503`(RPC만 검사), `tasks.md`의 8.6
   - 깨지는 것: 스펙은 "멤버가 사용량이나 잡에 이미 있는 `trace_id`를 넣어 새 턴을 시작하면 DB가 거부하고 상세 조회 권한은 변하지 않는다"고 한다. `0025:99`는 "이미 쓰인 trace로 새 턴을 만들 수 없습니다"라고 한다. 검사는 함수 안에만 있고, `authenticated`는 `ask_messages.trace_id`에 INSERT 권한이 있다. `design.md:170`이 같은 직접 INSERT를 인정하면서도 건수 위조만 다룬다.
   - 재현(viewer, 실제 API와 PostgREST, 워커 라우트):

     | 순서 | 결과 |
     | --- | --- |
     | 수집 trace 상세 | 403 |
     | `ask_threads` 생성 후 `ask_messages` 직접 INSERT, `trace_id`는 그 값 | **201** |
     | 같은 상세 | **200**, `calls`에 `compile` 행 |
     | 같은 `client_turn_id`로 `/ask` 재전달 | 200, `X-Trace-Id`가 그 값, 사용량 행 1 → **2** (`compile`, `query_embedding`) |

   - 같은 부류의 경로가 하나 더 있다. `enqueue_source_job`의 `p_trace_id`(`0023:128`, `:177`)는 값을 검사하지 않는다. owner가 viewer의 Ask trace로 잡을 만들자 상세가 403에서 200이 됐고(`control.py:369-384`) `calls`에 그 Ask 호출이 나왔다. 질문은 응답에 없다. 이는 `ai-control-room/spec.md:29-31`의 "editor가 다른 멤버의 Ask trace를 요청하면 403"도 그 editor가 직접 조작하면 성립하지 않는다는 뜻이다.
   - 영향 범위: 같은 워크스페이스 멤버 안에서만 일어난다. 돌아오는 `calls`는 요청자가 RLS로 직접 읽을 수 있는 값이다. 질문, 답변, 잡 payload는 나가지 않는다. 월 상한 합계는 실제 사용량만 더하므로 변하지 않는다. 바뀌는 것은 피해 trace의 상세 화면 합계에 공격자의 호출이 섞이는 것이다. 그래서 `blocked` 사유인 경계 붕괴는 아니다.
   - 조치: 둘 중 하나를 고른다.
     - **코드로 닫기**: 검사를 함수에서 `ask_messages`의 `before insert` 트리거(security invoker)로 옮긴다. 함수와 직접 INSERT가 함께 걸리고 존재 탐지 성질도 그대로다. `start_ask_turn`이 invoker라 `trace_id`의 INSERT 권한을 회수하는 방식은 쓸 수 없다. `0025`를 아직 고칠 수 있으므로 지금이 비용이 가장 작다. 회귀 테스트에 직접 INSERT를 더한다.
     - **기록으로 수용**: 스펙 시나리오를 "`start_ask_turn` 호출"로 좁히거나 삭제한다. `design.md:164`, `:167`과 `0025:99-103`에 "직접 INSERT와 `enqueue_source_job`으로 같은 일을 할 수 있어 이 검사는 경계가 아니다. 수용 근거는 새로 노출되는 값이 없다는 것이다"를 적는다. 이 경우 검사의 존재 이유 자체를 다시 판단해야 한다.
   - `enqueue_source_job` 경로는 어느 쪽을 고르든 design에 적으면 충분하다.

2. **`design.md:161`의 "예산 판정은 영향받지 않는다"가 거짓이다** (심각도: 낮음)
   - 위치: `openspec/changes/ai-control-flow-accounting/design.md:161`, 대비 `:169`
   - 깨지는 것: API 프로세스가 죽는 것은 워커 입장에서 클라이언트가 끊긴 것과 같다. 최종 사용량 프레임 전이면 비용 0으로 기록되어 상한에 쌓이지 않는다. `:169`가 정확히 이 사실을 적었으므로 같은 문서가 서로 모순된다. r2 지적 2의 정정이 한 곳을 빠뜨렸다.
   - 재현(실제 uvicorn 리스너, 스트림 스텁): 첫 델타 뒤 연결을 닫자 `record_usage`에 `usage={}`, `incomplete=True`가 전달됐고 `cost_micros({})`는 0이다.
   - 조치: "비용은 워커가 기록하지만, 최종 사용량 전에 끊기면 0으로 남아 상한을 비켜 갈 수 있다(아래 항목 참고)"로 고친다.

## 판정 근거

A-1, A-3, A-4는 모두 통과했고 테넌트 경계를 넘는 경로를 찾지 못했으므로 격리 관점의 `blocked` 조건은 아니다. 불변 규칙 위반도 없다. 다만 호출자가 정한 차단 사유 중 "근거가 사실과 다른 수용 기록"에 두 건이 해당한다. 지적 1은 스펙의 시나리오 문장이 재현으로 깨지고, 지적 2는 r2에서 지적한 것과 같은 거짓 문장이다. 코드 변경 없이 문서 정정만으로도 해소되므로 등급은 `needs_fix`다. 3라운드이므로 처리 절차는 프로젝트 규칙에 따른다.

## 참고: 차단 사유가 아닌 것

1. **내보내기 값의 잔여** (낮음): `_token`은 모양만 닫는다. `POLICYTEXT` 같은 ASCII 낱말은 `route.reason`, `policy_version`으로 64자까지 통과하고, `missing_channels`는 합쳐서 128자까지 통과한다. 공백과 한글은 막힌다. 내부 토큰이 있어야 하고 현재 API의 조립은 고정 값만 싣는다. 머리말(`ask_turn_export.py:9-11`)의 설명과 어긋나지 않는다.
2. **게이트웨이 설명은 확인된 사실이 아니다** (낮음, 기록 권고): `errors.py:72`는 "게이트웨이는 잘못된 `apikey`에도 401을 돌려주는데"라고 단정한다. 로컬 게이트웨이는 잘못된 `apikey`에 **200 `true`** 를 돌려주며, 클라우드 동작은 호출자도 확인하지 못했다. 코드 동작은 어느 쪽이든 안전하다. 코드 없는 401은 500이 되어 재로그인으로 위장되지 않는다. 클라우드에서 위조 JWT가 `PGRST30x` 없이 거부되더라도 r1 이전처럼 500이 될 뿐 임베딩 전에 멈춘다. 주석을 "그런 응답이 있다면"으로 바꾸고, `migration-0023-0026-record.md`의 클라우드 확인 목록에 "위조 토큰이 401인지 확인"을 한 줄 넣기를 권한다.
3. **#170의 문구** (낮음): 본문은 "턴이 끝나기 전"이지만 제목은 "스트림 수신 중"이고 완료 조건의 Given은 "검색 또는 스트리밍 단계"다. 종결 호출 중의 끊김과 전송 실패로 `streaming`에 남은 턴은 명시되어 있지 않다.
4. **사후 대조의 소유자** (낮음): `design.md:169`와 #170은 "Step 2의 범위"라고 하지만 `design.md:28`의 Step 2 목록에 없고 `:163`은 "후속 change"라고 한다. 이슈 검색에서 전담 이슈는 나오지 않았다. 수용의 근거는 유효하지만 후속 작업의 위치가 비어 있다.
5. **Langfuse 측 혼합** (낮음): 두 워크스페이스의 멤버는 한쪽의 trace로 다른 쪽에 턴을 만들 수 있다(200 실측). Postgres는 워크스페이스로 분리되지만 Langfuse trace ID는 trace 값만으로 만들어져(`observability.py:308`) 개발자용 사본에서 섞일 수 있다. r2가 적으라고 한 사실인데 `design.md:167`에는 없다.
6. **범위 밖, 기존 동작**: 같은 워크스페이스의 다른 멤버가 이미 쓰인 `client_turn_id`로 `/ask`를 부르면 `0019`의 유일 제약으로 500(23505)이 된다. 이번 변경과 무관하고 값을 추측할 수 없다.

## 재현 기록

스크립트는 저장소 밖에 있다. 실제 API 앱과 PostgREST, 실제 워커 라우트와 uvicorn을 쓰고 공급자만 스텁했다. SQL 실측은 전부 롤백했다.

### 재현 1: 새 검사의 거부와 정상 경로

| 호출 | 결과 |
| --- | --- |
| viewer, 사용량에 있는 Ask trace | 403 `42501` `trace already in use` |
| viewer, 사용량에 있는 수집 trace | 403 같음 |
| viewer, 잡에만 있는 trace | 403 같음 |
| 비멤버, 실재 trace와 부재 trace | 둘 다 403, 본문 동일 |
| 비멤버 `/ask` | 403 `forbidden` |
| `/ask` 새 턴 | 200, `done`, 사용량 1행 |
| 같은 턴 재전달 | 200, 같은 trace, `done`, 사용량 2행 |
| 다른 턴 | 200, 다른 trace |
| 재전달에 거부될 값 | 200, 저장된 trace 반환 |

### 재현 2: 401 매핑

| 호출 | 결과 |
| --- | --- |
| 영상 등록, `not-a-jwt` | **401** `unauthorized` (r2에서는 202 `failed`) |
| 영상 등록, anon 키 | 403 |
| 위조 JWT 원문 | 401 `PGRST301` |
| 잘못된 `apikey`와 유효한 JWT의 로컬 원문 | **200 `true`** |
| 전 라우트 매트릭스(본문 없는 호출) | 위조는 실재와 부재가 같다. 본문 필수 라우트는 양쪽 다 422 |

`/retrieval` 게이트는 r2 뒤에 파일이 바뀌지 않아 r2 재현을 그대로 인용한다.

### 재현 3: 리스너 종료

`_LISTENER_SHUTDOWN_SECONDS=1`, 실제 uvicorn, 진행 중 스트림 1건. 드레인이 받는 스냅샷에 기록 태스크가 실제로 들어 있는지 정리 지연을 바꿔 가며 봤다.

| 스트림 정리 지연 | 기록 지연 | 리스너 종료 | 스냅샷 | 기록 |
| --- | --- | --- | --- | --- |
| 0 | 0.3초 | 1.42초 | 1건 | 드레인 안에서 완료, `incomplete` |
| 0.01초 | 0.3초 | 1.42초 | 1건 | 같음 |
| 0.3초 | 0.3초 | 1.43초 | 1건 | 같음 |
| 2초 | 0.3초 | 1.43초 | 1건 | 같음 |
| 0 | 0 | 1.13초 | 1건 | 같음 |

취소 직후의 스냅샷이 비어 드레인이 헛도는 경합을 의심했지만 재현되지 않았다. 예산도 맞다. 리스너 15초 + 드레인 2초와 큐 20초 중 긴 쪽에 flush 3초를 더해 최악 23초 안팎이고 플랫폼 30초 안이다.

## 검증 범위

- 재현 스크립트:
  - `/private/tmp/claude-501/-Users-zorba-projects-NexusWiki/a44b5550-f4d4-4b96-b376-1e5e7a7a6cb1/scratchpad/r3_trace.py`
  - `/private/tmp/claude-501/-Users-zorba-projects-NexusWiki/a44b5550-f4d4-4b96-b376-1e5e7a7a6cb1/scratchpad/r3_shutdown.py`
  - `/private/tmp/claude-501/-Users-zorba-projects-NexusWiki/a44b5550-f4d4-4b96-b376-1e5e7a7a6cb1/scratchpad/r3_misc.py`
  - `/private/tmp/claude-501/-Users-zorba-projects-NexusWiki/a44b5550-f4d4-4b96-b376-1e5e7a7a6cb1/scratchpad/r3_misc2.py`
  - 기존 `/private/tmp/claude-501/-Users-zorba-projects-NexusWiki/a44b5550-f4d4-4b96-b376-1e5e7a7a6cb1/scratchpad/r2_export.py`, `/private/tmp/claude-501/-Users-zorba-projects-NexusWiki/a44b5550-f4d4-4b96-b376-1e5e7a7a6cb1/scratchpad/r2_matrix.py`
- `r2_lifecycle.py`는 리스너 구간의 설정 스텁이 새 인자 `timeout_graceful_shutdown`을 받지 못해 중단됐다. 코드 결함이 아니라 스크립트가 낡은 것이다. 해당 구간은 위 스크립트로 대체했고, 그 밖의 앞 구간 결과는 근거로 쓰지 않았다. `r2_repro.py`는 전체 재실행하지 않고 필요한 구간을 `r3_trace.py`로 옮겨 실행했다.
- 재현 데이터는 정리했다. 마지막 확인에서 `test-%` 사용자와 워크스페이스, 최근 10분 내 trace가 있는 잡이 모두 0건이다.
- 실행한 테스트: `test_db_error_mapping.py`, `test_ask_turn_export.py`, `packages/core/tests/test_observability.py` 합계 37 passed. 전체 스위트는 지시에 따라 돌리지 않았다.
- 실행하지 않음: 클라우드 환경, 실제 공급자, 실제 Langfuse 서버. 임시 프로젝트의 전체 적용과 전체 pytest는 호출자의 실행 결과를 전제로 받았고 직접 확인하지 않았다.
- r1의 간헐 실패: 이번에도 원인을 알아내지 못했다. 격리 스위트를 돌리지 않았으므로 해소되었다고 말할 수 없다.

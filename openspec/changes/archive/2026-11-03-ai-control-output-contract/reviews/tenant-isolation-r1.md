# Tenant Isolation 리뷰 — ai-control-output-contract r1

- 판정: needs_fix
- 대상: `git diff feat/ai-context-budget..HEAD` (`33ff943`, 호출자 지정 범위)
- 일시: 2026-11-02T16:17:44Z

## 검사 결과

| # | 항목 | 결과 | 근거 |
| --- | --- | --- | --- |
| A-1 | 사용자 경로의 service_role | 통과 | `GET /control/quality`와 Ask 수리·Fallback은 요청자 JWT의 `UserDb`만 쓴다. service_role은 `scripts/ask_replay.py`에만 있고 `assert_loopback`이 루프백으로 제한한다 |
| A-2 | 신규 테이블 RLS 동시 활성화 | 통과 | `0030:40`, 같은 트랜잭션. 카탈로그 `relrowsecurity=t` 확인 |
| A-3 | anon 신규 권한 | 통과 | 실측: anon은 `wiki_page_evidence` 조회와 `control_quality_snapshot` 실행 모두 permission denied. `replace_wiki_page_evidence`는 service_role만 실행 가능 |
| A-4 | 워커의 workspace_id 필터 | 통과 | `replace_wiki_page_evidence`가 `p_workspace_id`로 청크를 거른다. 실측: B 워크스페이스로 A 청크를 넘기면 0행, A 워크스페이스로 B 페이지를 넘기면 23503. `conflict.py`의 조회와 갱신도 전부 범위 지정 |
| A-5 | 복합 FK | 통과 | `0030:29-34` `(wiki_id, workspace_id)`, `(chunk_id, workspace_id)`. `raw_source_id`에는 FK가 없지만 RPC가 청크에서 파생시키고, 실측에서 원문 삭제 시 근거 행이 cascade로 0이 됐다 |
| B-6 | 0행 → 403 매핑 | 통과 | 신규 사용자 쓰기 경로 없음. `finalize_ask_turn`은 0행이면 42501을 던지는 구조 유지(`0029:66-68`) |
| B-7 | 42501 → 403 매핑 | 통과 | 비멤버 42501 실측, HTTP 403은 `test_control_quality_snapshot_enforces_tenant_and_role_boundaries` 통과. 빈 결과도 403(`control.py`) |
| C-8 | 핸들러 멱등성 | 통과 | 페이지 `(workspace_id, slug)` 업서트, 근거 `(wiki_id, chunk_id)` 기본키와 범위 교체. `latest_compile_fingerprint`가 성공 잡만 보므로 근거 저장 중 실패 후 재실행이 건너뛰어지지 않는다 |
| C-9 | jobs 직접 UPDATE 금지 | 통과 | diff에 직접 UPDATE 없음. `LlmSchemaError`는 기존 dead-letter 경로를 탄다 |
| D-10 | hnsw.iterative_scan | 해당 없음 | 제품 벡터 검색 변경 없음. `benchmark_retrieval.py`의 `relaxed_order`는 기준 브랜치에도 있고 제품 경로가 아니다 |
| D-11 | 토크나이저 일치 | 통과 | 앵커 제거 뒤의 본문으로 bigram을 만들고 `TSV_TOKENIZER_VERSION`을 함께 기록 |
| D-12 | search_tsv 생성 컬럼 | 해당 없음 | 변경 없음 |
| D-13 | 프롬프트 str.format | 통과 | 신규 코드에 없음. `repair_instruction`은 템플릿이 아니라 코드 조립 |
| D-14 | 인용 앵커 | 위반 | Fallback 제목과 단일 패스 제거에서 앵커 문법이 살아남는다 (조치 4, 5) |
| D | 조용한 실패·streaming 고착 (호출자 지정) | 위반 | 수리 입력 절단의 `ValueError`로 턴이 `streaming`에 남는다 (조치 1). 앵커만 있는 본문이 공백 페이지로 저장된다 (조치 3) |
| E-15 | 마이그레이션 번호 | 통과 | 기준 브랜치 최대 `0028`, 신규 `0029`~`0031`. `feat/ai-control-risk-policy`의 `0032`~`0034`가 그 뒤를 잇는다. 머지 순서를 지켜야 한다 |

### 호출자 지정 항목

| 항목 | 결과 | 근거 |
| --- | --- | --- |
| `0031` definer 권한 | 통과 | `search_path=''`, 첫 줄 역할 검사, authenticated만 실행. owner `postgres`(BYPASSRLS)이므로 이 검사가 유일한 경계이며 비멤버는 42501로 막힌다 |
| viewer 범위 | 통과 | 실측: viewer는 본인 7턴만, 수집·페이지 집계 0, owner는 8턴 전체 |
| control_report 조작: 집계 실패 | 통과 | 실측: 문자열·숫자·객체·배열·`null` 변형 7종을 넣어도 22P02 없이 집계되고 타입이 틀린 값은 세지 않는다 |
| control_report 조작: 수치 위조 | 참고 | 아래 「참고」 1 |
| 통제 보고서·사용량으로 본문 유출 | 통과 | `quality`는 코드와 불리언만. `_control_report`는 허용 필드 조립, `export_ask_turn`도 알려진 필드만 내보낸다. 구조화 위반은 코드만 `metadata`에 저장, 검증 메시지는 `blank_or_placeholder` |
| 수리 호출 비용 | 통과 | `reserve`가 호출마다 새 `p_call_id`를 쓰므로 두 번째 호출이 첫 예약에 합쳐지지 않는다. 예약 실패(402·422·503)는 `status>=400`으로 Fallback에 수렴 |
| 충돌 판정 쌍 격리 | 부분 위반 | 스키마 소진은 격리되고 잘못된 `disputed` 표시도 없다. 다만 `_retry_echo` 예외가 격리를 우회한다 (조치 2) |

## 조치가 필요한 항목

1. **수리 초안 절단의 ValueError로 턴이 `streaming`에 영구히 남는다** (심각도: 높음)
   - 위치: `apps/api/src/api/services/ask.py:622`(절단), `:636`(좁은 except), `:987`(호출부에 try 없음), 근본 원인 `packages/core/src/nexuswiki_core/context_budget.py:125`
   - 깨지는 것: `enc.encode(text)`는 본문에 `<|endoftext|>`가 있으면 `ValueError`를 던진다. `_repair_answer`는 `RuntimeError`와 `httpx.HTTPError`만 잡고, `ask()`의 호출부와 `_format_sse`에도 처리가 없다. 그래서 인용 없는 초안에 이 문자열이 있으면 `citations`와 `done` 없이 스트림이 끊기고 턴이 `streaming`에 남으며, 그 스레드를 열어 둔 화면은 `AskConversation.tsx:213-220`의 800ms 폴링을 계속한다. 스펙의 "수리 호출이 실패해도 `streaming`에 남지 않고 `fallback`"을 어긴다. 질문은 토크나이저를 거치지 않으므로 사용자가 이 문자열을 따라 쓰게 유도할 수 있다. 피해 범위는 본인 턴이다.
   - 실측: `_repair_answer`에 이 초안을 직접 넣어 `ValueError` 전파를 확인했다. 실제 공급자가 이 문자열을 출력하는 것과 HTTP 왕복 전체는 재현하지 않았고, 그 이후는 코드 경로로 판단했다.
   - 조치: `enc.encode(text, disallowed_special=())`로 근본 원인을 고치고, `_repair_answer`는 `except Exception`으로 `None`에 수렴시킨다(`CancelledError`는 `BaseException`이라 영향 없음). 이 초안으로 `fallback` 종결을 확인하는 회귀 테스트를 추가한다.

2. **워커의 `_retry_echo`도 같은 예외로 호출 상한과 쌍 격리를 우회한다** (심각도: 보통)
   - 위치: `apps/worker/src/worker/llm.py:337`, `:541`, 영향 `apps/worker/src/worker/handlers/conflict.py:133`
   - 깨지는 것: `_classify`는 예외를 던지지 않지만 그 뒤의 `_retry_echo`가 `ValueError`를 던진다(실측). `LlmSchemaError`가 아니므로 큐가 재시도해 "호출 2회 상한"이 깨지고(시도마다 1회씩, 큐 재시도 횟수만큼), 충돌 판정에서는 한 쌍의 문제로 잡 전체가 실패한다. 비용은 기록 뒤라 손실되지 않는다.
   - 조치: 조치 1의 `disallowed_special=()`로 함께 해결된다. `test_output_contract.py`에 회귀 테스트를 추가한다.

3. **앵커만 있는 본문이 검증을 통과해 공백 페이지로 저장된다** (심각도: 보통)
   - 위치: `apps/worker/src/worker/handlers/compile.py:95`(검증), `:394`(검증 뒤 제거)
   - 깨지는 것: `content="[[src:s1]] [[src:s2]]"`는 공백도 placeholder도 아니어서 통과하고(실측), 저장 직전 앵커 제거로 `" "`이 된다. `wiki_pages`에 본문 CHECK가 없어 공백 본문이 그대로 들어간다(실측). 잡은 성공하고 빈 페이지가 위키와 검색 대상에 남아 스펙의 "공백 페이지 MUST 거부"를 어긴다. `run_compile` 전체 실행이 아니라 검증, 정규식, DB 삽입을 각각 확인했다.
   - 조치: 검증기 안에서 앵커를 지운 값으로 공백과 placeholder를 판정해 재시도 경로에 태운다.

4. **Fallback이 제목의 앵커를 지우지 않아 발급 앵커로 잘못 해소된다** (심각도: 보통)
   - 위치: `packages/core/src/nexuswiki_core/answer_contract.py:108-110`, 공급원 `apps/worker/src/worker/handlers/compile.py:404`, `:407`
   - 깨지는 것: `_snippet`은 본문만 정리하고 제목은 그대로 싣는다. 컴파일도 본문의 앵커만 지우므로 제목과 별칭에 앵커가 저장될 수 있다. 실측: 제목 `제목 [[src:s1]] 와 [[wiki:w9]]`로 Fallback을 만들면 `[[src:s1]]`이 그 턴의 s1로 해소되어 제목 텍스트가 원문 인용처럼 보이고, `[[wiki:w9]]` 때문에 `fabricated_anchor_count=1`이 된다. "모델 없이 만들어 위조가 나올 수 없다"는 주석과 스펙의 "모든 앵커가 발급 앵커"에 어긋난다. 같은 워크스페이스 안의 인용 오염이며 테넌트 경계는 넘지 않는다.
   - 조치: 제목도 같은 정리를 거치게 하고, 컴파일이 `title`과 `aliases`의 앵커도 제거하게 한다.

5. **앵커 제거가 단일 패스여서 지운 자리에서 앵커가 다시 조립된다** (심각도: 보통)
   - 위치: `packages/core/src/nexuswiki_core/answer_contract.py:84`, `apps/worker/src/worker/handlers/parse.py:186`, `apps/worker/src/worker/handlers/compile.py:153`, `:167`, `:394`
   - 깨지는 것: 실측으로 원문 `[[wi[[wi[[src:x]]ki:y]]ki:w1]]`은 수집과 Fallback의 두 번 제거를 지나 답변에 `[[wiki:w1]]`을 남기고, 그 턴의 w1로 해소된다. `[[src[[wiki:a]]:s7]]`은 수집 뒤 청크에 `[[src:s7]]`로 저장된다. 따라서 "수집 시 지웠으므로 원문이 앵커를 위조할 수 없다"는 `compile.py:153` 주석이 사실이 아니고, `:167`의 부분 문자열 판정은 예산으로 잘린 s7까지 발급으로 볼 수 있다. 조작 원문을 넣을 수 있는 editor가 같은 워크스페이스 안에서 인용과 근거를 왜곡할 수 있다. 수집의 단일 패스 자체는 기존 동작이고, 이 change가 새로 그 전제에 의존한다.
   - 조치: 변화가 없을 때까지 반복 제거하는 공용 함수를 두고 세 곳에서 쓴다. 발급 판정은 문자열 검색 대신 `_join_within_budget`이 실제로 포함한 청크 수로 한다.

6. **재컴파일에서 사라진 페이지의 근거가 남는다** (심각도: 낮음)
   - 위치: `apps/worker/src/worker/handlers/compile.py`의 `_assign_slugs` 반복문
   - 깨지는 것: 교체는 이번 출력에 있는 페이지만 돈다. 재처리 업서트는 `(raw_source_id, chunk_index)`의 청크 id를 유지하므로, 빠진 페이지의 행은 내용이 바뀐 청크를 계속 근거로 가리킨다. 지금은 화면에 나오지 않고 `pages_with_evidence`에만 반영된다. `wiki_pages.sources`도 같은 동작이다. 코드 판독 결과이며 실행으로 재현하지는 않았다.
   - 조치: 근거를 표시하는 UI를 열기 전에, 이번 출력에 없는 페이지의 해당 원문 근거를 지운다.

7. **`ask_trace_aggregate`의 상태별 합이 전체와 맞지 않는다** (심각도: 낮음)
   - 위치: `supabase/migrations/0027_ask_cost_accounting.sql:436`, `apps/api/src/api/routers/control.py:459`
   - 깨지는 것: `turn_count`는 `fallback`을 포함하지만 `resolved_count`·`no_evidence_count`·`error_count` 어디에도 들어가지 않는다. 현재 화면은 질문 수와 오류만 표시하므로 API 응답에서만 드러난다. 코드 판독 결과다.
   - 조치: `fallback_count`를 추가하거나 합이 맞지 않는 이유를 응답 계약에 명시한다.

8. **수리 구간 소요 시간이 외부 관측에서 빠진다** (심각도: 낮음)
   - 위치: `packages/core/src/nexuswiki_core/observability.py:88`
   - 깨지는 것: `_SPAN_NAMES`에 `repair`가 없어 턴 내보내기에서 조용히 버려진다. 통제 보고서에는 남고 본문 유출은 아니다.
   - 조치: `repair`를 허용 목록에 추가한다.

## 참고 (지적 아님, 사람의 판단 대상)

1. **품질 수치는 멤버가 위조할 수 있다.** `0025` 컬럼 권한으로 작성자는 자기 턴의 `status`와 `control_report`를 직접 고칠 수 있다. 실측: viewer의 직접 UPDATE로 owner 화면의 `ask_fallback`과 `ask_violation_turns`가 늘었다. D9가 택한 내성은 "집계가 깨지지 않음"까지이고 수치의 진실성은 보장하지 않는다. 같은 워크스페이스 안의 문제이고 `0028`도 같은 구조다. 품질 탭을 신뢰 지표로 쓰려면 두 컬럼의 직접 UPDATE 권한을 회수하고 쓰기를 RPC로 제한해야 한다.
2. **클라이언트 끊김은 스펙상 범위 밖(#170)이지만 창이 넓어졌다.** 수리 중에는 바이트가 나가지 않아 끊김이 일어나기 쉽고, `CancelledError`는 다시 던져져 턴이 `streaming`에 남는다. 재전달이나 #170 처리 전까지 복구되지 않는다.

## 검증 범위

- 실행: `test_control_router`·`test_tenant_isolation_full_path`·`test_ask_router` 118 통과, `test_output_contract` 34 통과, `supabase/tests/wiki_page_evidence.sql`을 psql로 직접 실행해 종료 코드 0. `supabase test db`는 실행하지 않았다.
- 실행 안 함: 대시보드 테스트, typecheck, lint, 클라우드 확인, 실제 공급자 호출.
- ⚠️ **로컬 DB는 0031이 아니라 0034까지 적용되어 있다.** `schema_migrations`에 `feat/ai-control-risk-policy`의 `0032`~`0034`가 있다. 이 셋이 건드리는 것은 전역 Ask 템플릿과 신규 테이블·함수로, 위에서 확인한 객체를 재정의하지 않음을 소스로 확인했다. 그래도 위 DB 실측과 테스트는 이 브랜치의 스키마만으로 얻은 결과가 아니다.
- DB 실측은 모두 트랜잭션 롤백으로 수행했고 잔여 행 0을 확인했다.
- ⚠️ **이 보고서는 커밋 `33ff943` 기준이다.** 리뷰 막바지에 이 worktree에 커밋되지 않은 12개 파일 변경이 나타났다. 이 리뷰어가 만든 것이 아니며 검토하지 않았다. 실측과 줄 번호는 그 변경이 나타나기 전의 코드 또는 `git show HEAD:` 기준이다.

## 판정 근거

테넌트 경계를 넘는 경로는 찾지 못했다. A-1, A-3, A-4와 `0031` definer 경계는 실측으로 통과해 `blocked`에 해당하지 않는다. 다만 호출자가 지정한 "턴이 `streaming`에 남는 경로"가 조치 1로 실재하고, 공백 페이지 저장과 Fallback 인용 오염이 스펙의 MUST를 조용히 어긴다. 모두 코드 수정으로 해결되므로 `needs_fix`다. 조치 1~5를 고친 뒤 r2를 돌린다.

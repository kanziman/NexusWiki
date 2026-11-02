# Tenant Isolation 리뷰 — ai-control-output-contract r2

- 판정: needs_fix
- 대상: `git diff feat/ai-context-budget..HEAD` (`7700bd8`, 호출자 지정 범위). r1 이후 코드 변경은 `847c63d`
- 일시: 2026-11-02T16:38:00Z

## r1 항목 대조

| r1 항목 | HEAD 상태 | 근거 |
| --- | --- | --- |
| 1. 수리 초안 절단의 `ValueError`로 `streaming` 고착 | 해결 | `context_budget.py:126`, `chunking.py:90`이 `disallowed_special=()`로 바뀌었고, `ask.py:636`이 나머지 예외를 `None`으로 수렴한다. `encode` 호출은 이 두 곳뿐임을 확인했다. `test_special_token_in_the_draft_still_terminates_the_turn`, `test_unexpected_repair_failure_ends_in_fallback` 통과 |
| 2. `_retry_echo` 예외로 호출 상한과 쌍 격리 우회 | 해결 | 같은 수정. `test_special_token_output_stays_within_the_attempt_limit` 통과 |
| 3. 앵커만 있는 본문의 공백 페이지 저장 | 해결 | `compile.py:68`이 앵커 제거 후 판정한다. 실측: `[[src:s1]] [[src:s2]]`, `[[wi[[src:x]]ki:y]]`, `TODO [[src:s1]]` 모두 거부 |
| 4. Fallback 제목의 앵커 | 부분 해결 | Fallback 쪽은 해결(`answer_contract.py:112-113`). r1 조치의 후반부인 "컴파일이 `title`과 `aliases`의 앵커도 제거"는 없고 `design.md` Risks에도 없다 (조치 3) |
| 5. 단일 패스 앵커 제거 | r1 지정 위치는 해결 | `citations.py:46` 반복 제거, `parse.py:186`·`compile.py:161`·`:400`·`answer_contract.py:87`이 사용. `compile.py:173`의 `piece in source_content`도 조각 본문을 지운 뒤라 건전하다. 다만 반복 제거 자체가 새 문제를 만들었고(조치 2), `ask.py:262`는 단일 패스로 남았다(조치 5) |

항목 6~8과 품질 수치 위조, 클라이언트 끊김은 호출자 지시대로 판정 사유로 올리지 않았다.

## 검사 결과

| # | 항목 | 결과 | 근거 |
| --- | --- | --- | --- |
| A-1 | 사용자 경로의 service_role | 통과 | r1 이후 코드 diff에 `service_client`·`service_role` 추가 없음 |
| A-2 | 신규 테이블 RLS 동시 활성화 | 통과 | `33ff943..HEAD`의 `supabase/` 변경 없음. 카탈로그 `wiki_page_evidence.relrowsecurity=t` 재확인 |
| A-3 | anon 신규 권한 | 통과 | 실측: anon의 `control_quality_snapshot` 실행 권한 없음. 신규 GRANT 없음 |
| A-4 | 워커의 workspace_id 필터 | 통과 | 새 쿼리 없음. authenticated의 `replace_wiki_page_evidence` 실행 권한 없음. `supabase/tests/wiki_page_evidence.sql` 종료 코드 0 |
| A-5 | 복합 FK | 통과 | 스키마 변경 없음 (r1 결과 유지) |
| B-6 | 0행 → 403 매핑 | 통과 | 신규 사용자 쓰기 경로 없음 |
| B-7 | 42501 → 403 매핑 | 통과 | `test_tenant_isolation_full_path.py` 통과. viewer의 `structured`·`evidence`는 이제 `null`(`control.py:578`, `:588`) |
| C-8 | 핸들러 멱등성 | 통과 | 업서트 키 변경 없음. 다만 조치 3이 `(workspace_id, slug)`의 입력을 오염시킨다 |
| C-9 | jobs 직접 UPDATE 금지 | 통과 | 추가 없음 |
| D-10 | hnsw.iterative_scan | 해당 없음 | 제품 벡터 검색 변경 없음 |
| D-11 | 토크나이저 일치 | 통과 | `bigram(normalize(content))`가 앵커 제거 뒤 본문을 쓴다. `disallowed_special=()`는 tsv 토크나이저와 무관하다 |
| D-12 | search_tsv 생성 컬럼 | 해당 없음 | 변경 없음 |
| D-13 | 프롬프트 str.format | 통과 | 추가 없음 |
| D-14 | 인용 앵커 | 위반 | 인용 없는 단정 답변이 위반 없이 `resolved`가 된다(조치 1). 제목의 앵커가 Ask 컨텍스트에 실린다(조치 3) |
| D | 수정이 만든 조용한 실패 (호출자 지정) | 위반 | 조치 1, 2, 4 |
| E-15 | 마이그레이션 번호 | 통과 | `0029`~`0031`, 번호 변경 없음. `0032`~`0034`는 다른 브랜치 소유이므로 머지 순서를 지켜야 한다 |

### `repair` 구간의 표시 경로 (호출자 지정)

통과. 다만 이 경로를 잠그는 테스트가 없다. 저장소 테스트에 `"repair"` 구간 이름이나 `인용 수리` 라벨, `span_repair_ms`를 단언하는 곳이 없다.

| 단계 | 결과 |
| --- | --- |
| 기록 | 실측: 수리 성공과 수리 실패 후 Fallback 양쪽 모두 구간이 `retrieval, context, llm_stream, citation, repair` 순서로 저장된다 (`ask.py:987`) |
| API | 실측: `_spans`가 `("repair", "인용 수리")`를 돌려준다 (`control.py:77`) |
| Control Room | `ControlRoom.tsx:824`가 API 라벨을 그대로 표시하고 구간 이름별 분기가 없다. 코드 판독이며 브라우저로 보지는 않았다 |
| 외부 내보내기 | 실측: `export_ask_turn`의 메타데이터에 `span_repair_ms`가 실린다 (`observability.py:89`, `:218`) |
| 답변 본문 | `AskConversation.tsx:419`가 `citations.text`로 초안을 교체한다. 다시 열면 `:129`가 `message.status`로 Fallback 표시를 복원한다. 관련 테스트 통과 |

## 조치가 필요한 항목

1. **`없습니다` 대안 때문에 인용 없는 단정 답변이 위반 없이 `resolved`로 저장된다** (심각도: 높음, `847c63d`의 회귀)
   - 위치: `packages/core/src/nexuswiki_core/answer_contract.py:44-47`, 판정 `:60`
   - 깨지는 것: 새 정규식은 `자료|컨텍스트|근거|문서` 뒤 30자 안에 `없습니다`만 있으면 근거 부족 표현으로 본다. 문서를 다루는 제품이라 이 단어들은 일반 답변에 흔하다. 실측으로 `문서 업로드 크기에는 제한이 없습니다.`, `문서는 한 번 삭제하면 복구할 수 없습니다.`, `이 문서에 따르면 환불 수수료는 없습니다.`는 직전 정규식에서 위반이었는데 HEAD에서는 통과한다. API 전체 경로에서 첫 두 답변을 넣으면 enforce 모드에서 호출 1회, `p_status=resolved`, `violations=[]`, 인용 0개다. 수리도 Fallback도 없고 품질 탭의 위반 수에도 잡히지 않아, 이 change의 목표인 "인용 없는 답변의 `resolved` 저장 차단"이 보이지 않게 뚫린다. D5의 "표현을 놓치면 호출 1회가 더 들 뿐"은 반대 방향의 오판만 다룬다.
   - 조치: `없습니다` 단독 대안을 지운다. `(자료|컨텍스트|근거|문서)…(알|찾을|확인할|답할) 수 없습니다`처럼 종결형으로 제한하고 `(자료|컨텍스트|근거)(에|가) 없습니다`만 따로 둔다. 위 세 문장과 `자료에 따르면 환불 수수료는 없습니다.`, `문서를 찾을 수 없는 경우 재시도합니다.`를 위반 회귀 테스트로 넣는다.

2. **반복 앵커 제거가 입력 크기의 제곱으로 느려져 모든 테넌트가 공유하는 워커를 멈춘다** (심각도: 높음, `847c63d`의 회귀이며 r1 조치 5의 권고가 원인)
   - 위치: `packages/core/src/nexuswiki_core/citations.py:46`, 호출 `apps/worker/src/worker/handlers/parse.py:186`, 영향 `apps/worker/src/worker/__main__.py:270`, `:428`, `:436`
   - 깨지는 것: 중첩 깊이만큼 패스가 돌고 패스마다 전체를 훑는다. 실측(개발 머신): `"[[wi"*n + "[[src:x]]" + "ki:y]]"*n` 100,009자 1.09초, 200,009자 4.19초, 500,009자 25.97초다. 단일 패스는 500,009자에 1.16ms, 같은 크기의 정상 본문에 대한 `chunk_text`는 0.8초다. 코루틴 안에서 직접 호출하면 이벤트 루프가 26.05초 멈췄다. `parse.py:186`은 `to_thread` 없이 호출하고, 워커의 큐 루프와 내부 리스너(Ask LLM 스트림과 질의 임베딩)는 같은 이벤트 루프에 있다. 따라서 그동안 **모든 테넌트의** 잡과 Ask가 멈춘다. 입력 경로는 텍스트 수집(`MAX_TEXT_CHARS` 500,000자)이고, `text/plain` 업로드는 20 MiB까지 허용된다. 제곱 비례로 외삽하면 20 MiB는 수 시간이다(미실측). 같은 루프의 reaper도 멈추므로 복구가 재시작에 달리고, 재시작 뒤에는 at-least-once 재실행으로 같은 입력을 다시 처리한다. 데이터가 경계를 넘지는 않지만, editor 한 명이 다른 테넌트의 가용성을 해칠 수 있다.
   - 실측 범위: `strip_forged_anchors`와 이벤트 루프 지연을 직접 쟀다. `run_parse`나 실제 워커 프로세스로 재현하지 않았고, 루프 공유는 코드 판독이다.
   - 조치: 선형 스택 스캔으로 바꾸거나, 패스 수에 작은 상한을 두고 상한을 넘으면 남은 `[[`와 `]]`를 전부 지운다. 어느 쪽이든 재조립 불가를 유지하고, 500,000자 중첩 입력이 1초 안에 끝나는 회귀 테스트를 추가한다. `to_thread`만으로는 CPU 경합이 남아 부족하다.

3. **컴파일이 제목과 별칭의 앵커를 그대로 저장한다** (심각도: 보통, r1 항목 4의 잔여)
   - 위치: `apps/worker/src/worker/handlers/compile.py:382`, `:410`, `:413`, 소비처 `apps/api/src/api/services/ask.py:441`
   - 깨지는 것: 컴파일 입력에 앵커가 있어 모델이 제목에 베껴 쓸 수 있고, 검증기는 값을 바꾸지 않고 돌려준다. 실측: 제목 `제목 [[src:s1]]`, 별칭 `별칭 [[wiki:w1]]`이 그대로 저장되고 슬러그는 `제목-srcs1`이 된다. 같은 주제를 다음 컴파일이 `제목`으로 내면 슬러그가 달라 업서트되지 않고 페이지가 갈라진다. Ask 컨텍스트에는 `[[wiki:w1]] 제목 [[src:s1]]\n본문`이 실린다. 모델이 이를 따라 쓰면 그 턴의 무관한 s1으로 해소된다. `compile.py`가 본문에 대해 경고한 바로 그 혼동이다. 같은 워크스페이스 안의 문제다.
   - 조치: 슬러그 배정 전에 `title`과 `aliases`에서 앵커를 지운다. 이미 저장된 값을 위해 `_context_blocks`에서도 제목에 `strip_forged_anchors`를 적용한다. 같은 자리의 원문 청크 본문도 함께 적용하면 수집이 단일 패스였던 시기의 청크까지 막힌다.

4. **HTTP 200 오류 본문이 스키마 소진으로 처리되어 충돌 판정이 재시도 없이 성공으로 끝난다** (심각도: 보통, `847c63d`의 회귀)
   - 위치: `apps/worker/src/worker/llm.py:289-290`, 영향 `apps/worker/src/worker/handlers/conflict.py:133-134`
   - 깨지는 것: `847c63d` 전에는 본문 없는 응답이 `ProviderError`로 큐 재시도를 탔다. 지금은 `{"error": {...}}`처럼 공급자 장애를 뜻하는 응답도 `missing_content`다. 실측: 모든 호출이 이 응답이면 두 쌍에 호출 4회, 잡 성공, `disputed` 없음, 경고 로그만 남는다. 장애 창의 모순은 표시되지 않고, 원문이 바뀌어 다시 컴파일될 때까지 재판정 기회도 없다. 컴파일은 `dead`로 보이지만 일시 장애에도 큐 재시도를 잃는다. 비용이 청구된 `content: null`을 상한 안에 두는 것은 spec-conformance r1의 지적대로 맞다. 문제는 청구되지 않은 오류 응답까지 같은 코드로 묶인 점이다.
   - 판단 근거의 한계: 스펙은 "공급자 전송 실패는 재시도 대상"이라고만 하고 200 오류 본문은 정하지 않았다. 실제 공급자가 비스트리밍에서 이 형태를 내는지는 재현하지 않았고, 스트림에서 내는 것은 `ask.py`의 `_delta_text` 주석에 기록돼 있다.
   - 조치: 최상위 `error`가 있고 `usage`가 없는 응답은 `ProviderError`로 올려 큐 재시도에 맡긴다. 또는 이를 Risks에 명시해 사람이 결정하게 한다.

5. **모델 출력의 단일 패스 제거로 미발급 앵커가 저장 본문에 재조립된다** (심각도: 낮음, r1 항목 5와 같은 부류)
   - 위치: `apps/api/src/api/services/ask.py:262`
   - 깨지는 것: 실측: `답 [[src:s1]]. 다른 문장 [[wi[[wiki:foo]]ki:w9]].`는 `rendered_text`에 `[[wiki:w9]]`를 남기고 `fabricated_anchor_count=0`, `unsourced_sentence_ratio=0.0`을 돌려준다. 안쪽이 `ISSUED` 모양이 아니어서 위조로 세지 않으므로 수리도 돌지 않고, 근거 없는 문장이 인용된 문장으로 계산된다. 화면은 `resolved`에 없는 별칭을 지우므로 w9는 보이지 않지만, 재조립된 별칭이 그 턴에 다른 곳에서 인용됐다면 이 자리에 마커가 뜬다. `847c63d`의 AC "답변의 앵커는 발급된 것뿐"에 어긋난다. 재현은 모델 출력에 이 문자열이 있어야 한다.
   - 조치: `_strip_fabricated` 치환을 변화가 없을 때까지 반복한 뒤의 텍스트로 앵커를 판정하고 지표를 잰다. 입력은 모델 출력 크기로 제한되지만 조치 2의 방식과 맞춘다.

## 검증 범위

- HEAD에서 실행: `test_ask_router`, `test_control_router`, `test_tenant_isolation_full_path`, `test_output_contract`, `test_llm_gateway`, `test_answer_contract`, `test_context_budget` 202 통과, 1 오류.
- ⚠️ 오류는 `test_each_table_has_owner_control_and_bidirectional_foreign_read_denial[jobs]`의 설정 단계다. 출력을 잘라 원인은 확인하지 못했다. 해당 테스트 함수 단독 재실행은 9 통과, 파일 전체 재실행은 40 통과다. 이 파일 재실행의 일부 또는 전부는 아래의 미커밋 변경이 있는 상태에서 돌았다.
- 대시보드: `git archive HEAD`로 뽑은 사본에서 `ControlRoom`, `AskThreadHistoryRestore` 17 통과. typecheck와 lint는 실행하지 않았다.
- 조치 1~5의 재현은 저장소 밖 임시 테스트로 했다. 실제 공급자 호출과 클라우드 확인은 하지 않았다.
- ⚠️ 로컬 DB는 `0034`까지 적용된 상태이고, `0032`~`0034`는 다른 브랜치 소유다. DB 결과는 이 브랜치 스키마만으로 얻은 것이 아니다.

### 리뷰 중 나타난 미커밋 변경

2026-11-02T16:34Z(KST 01:34) 무렵 worktree에 커밋되지 않은 11개 파일 변경이 나타났다. 이 리뷰어가 만든 것이 아니다. 판정, 줄 번호, 조치 1~5의 재현은 모두 `7700bd8` 기준이다. 판정 대상은 아니지만 다음 라운드에 영향을 주는 관찰만 적는다.

- 조치 1: 미커밋 정규식 사본으로 확인하니 `문서 업로드 크기에는…`과 `복구할 수 없습니다`는 위반으로 돌아온다. 그러나 `자료에 따르면 환불 수수료는 없습니다.`와 `문서를 찾을 수 없는 경우 재시도합니다.`는 여전히 근거 부족으로 통과한다.
- 조치 4: 미커밋 `llm.py`는 2xx의 깨진 본문까지 `missing_content`로 묶어 범위를 넓힌다. 호출 상한에는 맞지만 충돌 판정에서 조용히 넘어가는 경우가 늘어난다.
- `0031` 미커밋 변경은 반환 컬럼을 추가한다. 로컬 DB 재적용 여부는 확인하지 않았다.

## 판정 근거

테넌트 데이터 경계를 넘는 경로는 찾지 못했다. A-1, A-3, A-4는 통과했고 r1 이후 SQL 변경도 없어 `blocked`에 해당하지 않는다. r1 항목 1~3은 해결됐고 `repair` 표시 경로도 정상이다. 그러나 수정이 두 가지 높은 심각도의 회귀를 만들었다. 인용 없는 답변이 위반 기록 없이 `resolved`로 저장되는 경로가 넓어졌고, editor 한 명의 입력이 공유 워커를 멈출 수 있게 됐다. 조치 3은 r1 항목 4의 미처리 잔여다. 모두 코드 수정으로 해결되므로 `needs_fix`다. 다음이 3라운드이므로, 거기서도 `pass`가 아니면 `blocked`로 확정해 사람에게 넘겨야 한다.

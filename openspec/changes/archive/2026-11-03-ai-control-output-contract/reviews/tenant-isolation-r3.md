# Tenant Isolation 리뷰 — ai-control-output-contract r3

- 판정: blocked
- 대상: `git diff feat/ai-context-budget..HEAD` (`03dbad2`, 호출자 지정 범위). r2 이후 코드 변경은 `7bbe687`이고 `03dbad2`는 증거 파일만 바꾼다
- 일시: 2026-11-02T21:45:00Z

`blocked`는 최대 3라운드 규칙(`.claude/CLAUDE.md` 「리뷰 게이트」)에 따른 확정이다. 테넌트 경계를 넘는 경로는 찾지 못했고, 남은 지적의 성격은 코드 수정으로 해결되는 `needs_fix`다.

## r2 항목 대조

| r2 조치 | 대상 | HEAD 상태 | 근거 |
| --- | --- | --- | --- |
| 1 | 근거 부족 판정 | 부분 해결 | `없습니다` 단독 대안은 사라졌다. r2가 지정한 회귀 문장 5개 중 `문서를 찾을 수 없는 경우 재시도합니다.`는 여전히 위반 없이 통과한다 (아래 조치 1) |
| 2 | 앵커 제거의 시간 상한 | 해결, 새 결함 | 실측: 중첩 620,009자 0.015초, 21,000,009자 0.466초. 평면 앵커와 닫히지 않은 앵커도 약 2,100만 자에 0.2초 미만이다. r2의 500,009자 25.97초와 대비된다. 다만 상한 초과 시 쓰는 마무리 단계가 앵커를 남긴다 (아래 조치 2) |
| 3 | 제목과 별칭의 앵커 | 부분 해결 | 새 컴파일 쓰기는 해결됐다(`compile.py:65`, `:78`, `:106`). r2 조치 후반의 `_context_blocks` 제거는 없고 `design.md` Risks에도 없다 (아래 조치 4) |
| 4 | 200 오류 본문의 재시도 | 해결 | 실측: 최상위 `error`이면 호출 1회, `ProviderError`, 비재시도 목록 아님, 잡 완료 0회, 표시 없음. `design.md` Risks에 기록됨. 아래 「관찰」 참고 |
| 5 | 모델 출력의 재조립 | 부분 해결 | 깊이 8까지는 제거되고 지표도 맞다. 깊이 9 이상은 미발급 앵커가 남는다 (아래 조치 3) |

## 검사 결과

| # | 항목 | 결과 | 근거 |
| --- | --- | --- | --- |
| A-1 | 사용자 경로의 service_role | 통과 | 범위 전체 diff에 `service_client(` 추가 없음 |
| A-2 | 신규 테이블 RLS 동시 활성화 | 통과 | `0030:19` 생성, `:40` 같은 마이그레이션에서 활성화. 카탈로그 `relrowsecurity=t` |
| A-3 | anon 신규 권한 | 통과 | 실측: anon의 `control_quality_snapshot` 실행 권한 없음. diff에 anon GRANT 없음 |
| A-4 | 워커의 workspace_id 필터 | 통과 | r2 이후 새 쿼리 없음. authenticated의 `replace_wiki_page_evidence` 실행 권한 없음. `supabase/tests/wiki_page_evidence.sql` 종료 코드 0 |
| A-5 | 복합 FK | 통과 | `0030:29-33`이 `(wiki_id, workspace_id)`, `(chunk_id, workspace_id)`를 나른다 |
| B-6 | 0행 → 403 매핑 | 해당 없음 | 신규 사용자 쓰기 경로 없음 |
| B-7 | 42501 → 403 매핑 | 통과 | `test_tenant_isolation_full_path.py`, `test_db_error_mapping.py` 통과. `0031`의 `missing_content`도 `v_can_view_ws` 조건 안에 있고, viewer의 `structured`는 `null`이다 |
| C-8 | 핸들러 멱등성 | 통과 | 업서트 키 변경 없음. `provider_error`는 쓰기 전에 던지고, 충돌 판정 재실행은 쌍을 다시 판정하지만 `disputed` 표시는 멱등이다 |
| C-9 | jobs 직접 UPDATE 금지 | 통과 | 추가 없음 |
| D-10 | hnsw.iterative_scan | 해당 없음 | 제품 벡터 검색 변경 없음 |
| D-11 | 토크나이저 일치 | 통과 | `bigram(normalize(content))`가 정리된 본문을 쓴다 |
| D-12 | search_tsv 생성 컬럼 | 해당 없음 | 시도 없음 |
| D-13 | 프롬프트 str.format | 통과 | 추가 없음 |
| D-14 | 인용 앵커 | 위반 | 인용 없는 단정 답변이 `resolved`가 되고(조치 1), 수집 제거를 통과한 앵커가 Ask 컨텍스트에 실린다(조치 2) |
| D | 수정이 만든 조용한 실패 (호출자 지정) | 위반 | 조치 2 |
| E-15 | 마이그레이션 번호 | 통과 | `0029`~`0031`. `0031`을 제자리에서 고쳤지만 `docs/reference/stack.md:79`가 운영 미적용이라 하고, 로컬 함수에도 `structured_missing_content`가 있다. `feat/ai-control-risk-policy`의 `0032`~`0034`는 이 브랜치의 HEAD를 포함하지 않으므로 이 브랜치가 먼저 클라우드에 나가야 한다 |

## 조치가 필요한 항목

1. **근거 부족 표현이 답변 어디에 있든 전체를 면제해, 인용 없는 단정 답변이 위반 없이 `resolved`로 저장된다** (심각도: 높음, r2 조치 1의 잔여)
   - 위치: `packages/core/src/nexuswiki_core/answer_contract.py:45-46`, 판정 `:62`
   - 깨지는 것: 첫 대안은 종결형이 아니고(`알\s*수\s*없`) `문서`도 받으며, 판정은 전체 텍스트의 `search`다. API 전체 경로 실측에서 다음 세 답변 모두 enforce 모드에서 호출 1회, `p_status=resolved`, `violations=[]`, `resolved=[]`였다.
     - `문서를 찾을 수 없는 경우 재시도합니다.` (r2가 지정한 문장)
     - `문서 권한이 없으면 내용을 확인할 수 없습니다.`
     - `환불은 구매 후 7일 이내에 가능합니다. 부분 환불 여부는 제공된 자료로는 알 수 없습니다.`
   - 셋째가 가장 나쁘다. 표현 하나가 앞 문장의 근거 없는 단정까지 면제한다. 수리도 Fallback도 없고 품질 탭의 위반 수에도 잡히지 않아 이 change의 목표인 "인용 없는 답변의 `resolved` 저장 차단"이 보이지 않게 뚫린다. D5의 "놓쳐도 수리 호출 1회"는 반대 방향의 오판만 다룬다. 시드 지시문(`0006:151`)은 근거 부족 문구 뒤에 한 줄을 덧붙이라고 하므로 "모든 문장이 표현과 일치"로 좁히면 정상 답변이 위반이 된다.
   - 스펙의 한계: `grounded-answering` 스펙은 근거 부족과 단정이 섞인 답변을 정하지 않았다. 셋째의 판정 기준은 사람이 정해야 한다.
   - 조치: 첫 대안을 `(자료|컨텍스트|근거)(로는|만으로는|에서는?|에는)…(알|찾을|확인할|답할)\s*수\s*없습니다`처럼 자료를 가리키는 조사와 종결형으로 제한하고 `문서`를 뺀다. 근거 부족 표현이 첫 문장일 때만 면제한다. 오탐 비용은 수리 호출 1회로 D5가 이미 받아들였다. 위 세 문장을 위반 회귀 테스트에, `제공된 자료로는 알 수 없습니다. 환불 정책 문서가 필요합니다.`를 통과 테스트에 넣는다.

2. **앵커 제거의 마무리 단계가 앵커를 되살려, 수집한 원문에 위조 앵커가 저장된다** (심각도: 보통, `7bbe687`의 회귀)
   - 위치: `packages/core/src/nexuswiki_core/citations.py:55`, 호출 `apps/worker/src/worker/handlers/parse.py:186`, `apps/worker/src/worker/handlers/compile.py:65`, 소비처 `apps/api/src/api/services/ask.py:454`
   - 깨지는 것: `str.replace("[[", "[ [")`는 겹치지 않게 치환하므로 홀수 개의 연속 `[`에서 `[[`가 남는다. 여덟 번째 패스 뒤에 `[[[wiki:w1]]`이 되도록 깊이 8 중첩 앞에 `[`를 하나 붙이면 된다. 실측: `"정상 문장입니다. [" + "[[wi"*8 + "[[wiki:w8]]" + "ki:w1]]"*8 + " 위조된 주장."`을 `run_parse`에 넣으면 청크가 `정상 문장입니다. [ [[wiki:w1]] 위조된 주장.`으로 저장된다. "앵커가 될 수 없게 만든다"는 `citations.py:49` 주석이 사실이 아니고, 함수가 멱등하지도 않다(재호출하면 지워진다).
   - 영향: `_context_blocks`가 이 청크를 다시 지우지 않아 프롬프트에 그대로 실린다. 모델이 이를 베껴 쓴 문자열을 `resolve_citations`에 넣으면 `w1`로 해소되고 `fabricated_anchor_count=0`이다. 근거 없는 주장이 그 턴의 다른 위키를 인용한 것처럼 보이고, r1 조치 5와 같은 왜곡이 되살아난다. `CompiledPage`에서도 같은 입력이 살아남아 제목 `제목 [ [[wiki:w1]]`, 슬러그 `제목-wikiw1`이 되므로 r2 조치 3의 보호도 뚫린다. 컴파일 입력(`compile.py:171`)과 Fallback(`answer_contract.py:89`)은 재호출 덕분에 안전하다. 조작 원문을 넣을 수 있는 editor가 필요하고 같은 워크스페이스 안의 문제다.
   - 놓친 이유: `test_deep_nesting_is_stripped_in_bounded_time`(`test_answer_contract.py:157`)은 깊이 80,000의 앞에 `[`가 없는 입력만 본다.
   - 조치: `re.sub(r"\[(?=\[)", "[ ", text)`로 바꿔 인접한 `[`를 전부 끊는다. 깊이 1~12와 앞붙임 `[` 0~3개의 조합에서 결과에 `BROAD_ANCHOR_PATTERN`이 없고, 재호출해도 같은 값인지 단언하는 테스트를 넣는다.

3. **모델 출력의 재조립 제거에 마무리 단계가 없어 깊이 9 이상에서 미발급 앵커가 남는다** (심각도: 낮음, r2 조치 5의 잔여)
   - 위치: `apps/api/src/api/services/ask.py:82`, `:265`
   - 깨지는 것: 실측: 깊이 9의 `답 [[src:s1]]. 다른 문장 [[wi…[[wiki:x]]…ki:w9]].`는 `rendered_text`에 `[[wiki:w9]]`를 남기고 `fabricated_anchor_count=0`, `unsourced_sentence_ratio=0.0`이다. 위반이 아니므로 그대로 저장되고 근거 없는 문장이 인용된 문장으로 계산된다. 깊이 8까지는 정상이다(`unsourced_sentence_ratio=0.5`). 재현은 모델 출력에 이 문자열이 있어야 한다.
   - 조치: 횟수를 다 쓰고도 `BROAD_ANCHOR_PATTERN`에 맞는 미발급 앵커가 남으면 조치 2와 같은 방식으로 끊는다. 깊이 9 회귀 테스트를 넣는다.

4. **Ask 컨텍스트가 저장된 제목과 청크의 앵커를 지우지 않는다** (심각도: 낮음, r2 조치 3의 잔여)
   - 위치: `apps/api/src/api/services/ask.py:446-448`, `:454`
   - 깨지는 것: 실측: 제목이 `제목 [[src:s1]]`인 위키는 컨텍스트에 `[[wiki:w1]] 제목 [[src:s1]]`로 실린다. 새 컴파일은 제목을 정리하지만, 이미 저장된 값과 수집이 단일 패스였던 시기의 청크는 그대로다. 그런 값이 운영에 실제로 있는지는 확인하지 않았다.
   - 조치: `_context_blocks`에서 제목과 본문에 `strip_forged_anchors`를 적용한다. 조치 2의 2차 방어선도 된다.

## 관찰 (판정 사유 아님)

- `design.md` Risks의 "그 밖의 깨진 200 응답"에 해당하므로 사유로 올리지 않았다. `choices[0].error` 형태는 mock 실측에서 두 쌍에 호출 4회, 잡 성공, 표시 없음이다. 즉 최상위 `error`와 달리 r2 조치 4의 증상이 이 형태에는 남는다. 실제 공급자가 비스트리밍에서 이 형태를 내는지는 확인하지 않았다.

## 검증 범위

- 코어와 워커(`test_answer_contract`, `test_context_budget`, `test_settings`, `test_output_contract`, `test_llm_gateway`, `test_llm`, `test_handlers`, `test_controlled_ai_evidence`): 183 통과.
- API(`test_ask_citations`, `test_ask_router`, `test_control_router`, `test_tenant_isolation_full_path`, `test_db_error_mapping`): 132 통과.
- 파이프라인(`test_pipeline_e2e`, `test_reingestion_idempotency`, `test_queue_baseline`): 15 통과. 실패가 없어 단독 재실행은 필요 없었다. `test_queue`와 나머지 테스트 파일은 돌리지 않았다.
- 대시보드: `ControlRoom`, `AskThreadHistoryRestore` 17 통과. typecheck와 eslint는 실행하지 않았다. 브라우저로 보지 않았다.
- ruff는 변경된 소스 5개 파일에만 돌렸고 통과했다.
- 조치 1~4의 재현은 저장소 밖 임시 테스트로 했다. 공급자는 모두 mock이다. "모델이 앵커를 베껴 쓴다"는 해당 문자열을 직접 넣어 확인한 것이고, 실제 모델이 베끼는지는 재현하지 않았다. 앵커 제거 시간은 함수를 직접 쟀고 실제 워커 프로세스로 재지 않았다. 클라우드는 확인하지 않았다.
- ⚠️ 로컬 DB는 `0034`까지 적용된 상태이고 `0032`~`0034`는 다른 브랜치 소유다. DB 결과는 이 브랜치 스키마만으로 얻은 것이 아니다.

## 판정 근거

A-1, A-3, A-4는 통과했고 테넌트 데이터가 경계를 넘는 경로는 찾지 못했다. 시간 상한과 최상위 `error` 본문 재시도는 해결됐다. 그러나 인용 없는 단정 답변이 위반 기록 없이 `resolved`로 저장되는 경로가 남았고(조치 1), 시간 상한 수정의 마무리 단계가 조작 원문의 앵커를 청크에 저장한다(조치 2). 둘 다 이중 Citation을 조용히 무너뜨리므로 `pass`가 아니다. 등급 조건만 보면 `needs_fix`지만, 3라운드에서 `pass`가 아니므로 규칙에 따라 `blocked`로 확정해 사람에게 넘긴다. 사람이 결정할 것은 네 가지 수정을 추가 라운드로 받을지와, 조치 1에서 근거 부족과 단정이 섞인 답변을 어떻게 판정할지다.

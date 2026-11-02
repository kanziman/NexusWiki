# Spec Conformance 리뷰 — ai-control-output-contract r4

- 판정: needs_fix
- 대상: `git diff feat/ai-context-budget..HEAD` (`45ec35bd31f2cc79d8a76efb3897934d427693ea`, 스택된 브랜치라 main이 아니라 이 범위로 봤다). r3 이후 변경은 `9976b9d`, `45ec35b`이다
- 일시: 2026-11-03T07:20:00+09:00

## 요약

r3 지적 3건은 모두 해결됐다. 수정으로 깨진 시나리오도 찾지 못했다. Scenario 29개 중 충족 28개, 부분 충족 1개, 미충족 0개다.

남은 지적은 1건이다. 이번에 추가된 Scenario "HTTP 200 본문의 공급자 오류"의 THEN 중 "충돌 판정이 판정 없이 성공으로 끝나지 않는다"를 확인하는 테스트가 없다. 동작 자체는 맞다(실측). `conflict.py:133`을 `except Exception:`으로 바꿔도 관련 테스트 170개가 전부 통과하는 것을 확인했다. 테스트 하나를 더하면 해결된다.

합성 입력으로만 재현되는 항목은 호출자 지시에 따라 판정에 넣지 않고 「비차단 관찰」에 적었다. 그중 관찰 1은 스펙 WHEN에 문자 그대로 해당하므로 먼저 읽기를 권한다.

## r3 지적 대조

| # | r3 지적 | 결과 | 증거 |
| --- | --- | --- | --- |
| 1 | 근거 부족 판정이 양쪽으로 어긋난다 | 해결 | `packages/core/src/nexuswiki_core/answer_contract.py:44-64`, `:77`. r3가 조건으로 삼은 문장을 `_ask_with_mode`로 Ask 경로에서 실측했다. 과대 일치 3문장은 모두 호출 2회, 위반 `no_citation`, 수리 후 `resolved`다. `제공된 자료로는 답변할 수 없습니다.`는 호출 1회, 위반 없음이다. 테스트 `packages/core/tests/test_answer_contract.py:57-70`, `:144-159` |
| 2 | `usage`의 깨진 값이 호출 상한과 비용 기록을 빠져나간다 | 해결 | `apps/worker/src/worker/llm.py:306-309`, `:512-535`. r3의 세 입력(`"abc"`, `[1]`, `1e999`)을 정상 출력과 깨진 출력으로 각각 실측했다. 정상은 호출 1회·1행, 깨진 출력은 호출 2회·2행, `LlmSchemaError`(비재시도)다. 테스트 `apps/worker/tests/test_output_contract.py:576`. 같은 부류의 잔여 입력은 관찰 2 |
| 3 | `missing_content` 양수 집계 테스트가 없다 | 해결 | 시드 `apps/api/tests/test_control_router.py:877-892`, 단언 `:918`, `:921`. 대시보드 `apps/dashboard/tests/ControlRoom.test.tsx:474`, `:496`. `control.py:586`의 키를 틀리게 바꾼 복사본에서 이 테스트가 실패하는 것을 확인했다 |

r3의 「사람 확인 사항」(200 `error` 본문)은 사용자 결정으로 스펙에 반영됐다(`specs/wiki-compilation/spec.md:19`, `:25-27`, `design.md:68`). r3 참고 사항의 깊은 중첩 앵커 잔존도 해결됐다(`apps/api/src/api/services/ask.py:275-279`, 테스트 `apps/api/tests/test_ask_citations.py:56`).

## 시나리오 판정

### grounded-answering

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| Ask 인용 계약과 수리 / 인용이 하나도 없는 답변을 수리한다 | 충족 | `ask.py:994-1025`, `:1040-1050` · 테스트 `apps/api/tests/test_ask_router.py:1061` |
| Ask 인용 계약과 수리 / 근거 부족을 밝힌 답변 | 충족 | `answer_contract.py:55-64` · 테스트 `test_ask_router.py:1084`, `test_answer_contract.py:57-70` |
| Ask 인용 계약과 수리 / 단정과 근거 부족이 섞인 답변 | 충족 (관찰 1) | `answer_contract.py:62-64`, `:77`, `ask.py:1003-1025` · 테스트 `test_answer_contract.py:144-159`. Ask 경로 전체를 도는 테스트는 없고 실측했다(호출 2회, 수리 후 `resolved`) |
| Ask 인용 계약과 수리 / 정상 답변 | 충족 | `answer_contract.py:75-79` · 테스트 `test_ask_router.py:1046`, `test_answer_contract.py:80` |
| 결정론적 Ask Fallback / 수리도 실패한다 | 충족 | `ask.py:1026-1032`, `answer_contract.py:110-145` · 테스트 `test_ask_router.py:1095`, `test_answer_contract.py:91` |
| 결정론적 Ask Fallback / 수리 호출 자체가 실패한다 | 충족 | `ask.py:647-648`, `:653-658` · 테스트 `test_ask_router.py:1095`, `:1134`, `:1143` |
| 결정론적 Ask Fallback / 근거 본문에 앵커 문법이 들어 있다 | 충족 | `answer_contract.py:102-107`, `:129-131`, `packages/core/src/nexuswiki_core/citations.py:42-65` · 테스트 `test_answer_contract.py:91`, `:105`, `:165`, `:178` |
| 결정론적 Ask Fallback / 기록을 다시 연다 | 충족 | `apps/dashboard/components/AskConversation.tsx:49`, `:129`, `:689` · 테스트 `apps/dashboard/tests/AskThreadHistoryRestore.test.tsx:182`. 근거 목록 본문까지 단언하지는 않는다 |
| 품질 통제 모드 / shadow 모드의 위반 | 충족 | `ask.py:994-1003` · 테스트 `test_ask_router.py:1119` |
| 품질 통제 모드 / off 모드 | 충족 | `ask.py:994` · 테스트 `test_ask_router.py:1127` |

### wiki-compilation

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| 코드 펜스와 의미 검증 / 펜스로 감싼 정상 JSON | 충족 | `llm.py:548-564` · 테스트 `test_output_contract.py:111`, `apps/worker/tests/test_controlled_ai_evidence.py`의 `compile_fence_retry` |
| 코드 펜스와 의미 검증 / placeholder 페이지 | 충족 | `apps/worker/src/worker/handlers/compile.py:65-75`, `:105` · 테스트 `test_output_contract.py:175`, `:495` |
| 코드 펜스와 의미 검증 / 본문이 템플릿 문법을 설명한다 | 충족 | `compile.py:59-61` · 테스트 `test_output_contract.py:187` |
| 호출 상한 / 어떤 입력에도 호출은 2회를 넘지 않는다 | 충족 (관찰 2, 3) | `llm.py:270-357` · 테스트 `test_output_contract.py:125`, `:140`, `:369`, `:511`, `:576` |
| 호출 상한 / HTTP 200 본문의 공급자 오류 | 부분 충족 | 동작은 충족한다. `llm.py:289`, `:315-327`, `:483-489`, `apps/worker/src/worker/handlers/conflict.py:133`. 실측: 최상위와 `choices[0]`의 `error` 모두 `run_conflict_check`가 호출 1회, 기록 1행(`provider_error`), `complete` 0회, `disputed` 없음, `ProviderError`(재시도 대상)로 끝난다. 테스트는 게이트웨이까지다(`test_output_contract.py:532`, `:603`). 충돌 판정 절을 확인하는 테스트가 없다 (조치 항목 1) |
| 호출 상한 / 파싱할 수 없는 출력의 재시도 | 충족 | `llm.py:567-575` · 테스트 `test_output_contract.py:145`, `:156`, `:443` |
| 페이지 근거 청크 / 발급되지 않은 앵커 | 충족 | `compile.py:171`, `:180`, `:287`, `:440-451` · 테스트 `test_output_contract.py:343`, `:416`, `:460` |
| 페이지 근거 청크 / 재컴파일 | 충족 | `supabase/migrations/0030_wiki_page_evidence.sql:68-80` · 테스트 `supabase/tests/wiki_page_evidence.sql` (직접 실행 통과). 핸들러를 두 번 도는 테스트는 없다 |
| 페이지 근거 청크 / 다른 워크스페이스 사용자의 조회 | 충족 | `0030:43-48` · 테스트 `supabase/tests/wiki_page_evidence.sql` (직접 실행 통과) |
| 충돌 판정 쌍 격리 / 한 쌍만 스키마를 어긴다 | 충족 | `conflict.py:125-135` · 테스트 `test_output_contract.py:242`, `:424` |

### ai-control-room

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| 품질 탭 / editor가 품질 탭을 연다 | 충족 | `apps/api/src/api/routers/control.py:544-597`, `supabase/migrations/0031_control_quality_tab.sql:95`, `:127`, `apps/dashboard/components/ControlRoom.tsx:549-614` · 테스트 `test_control_router.py:816`, `:918-921`, `ControlRoom.test.tsx:452`, `:496` |
| 품질 탭 / viewer가 품질 탭을 연다 | 충족 | `control.py`의 `can_view` 분기, `0031` · 테스트 `test_control_router.py:816`(viewer 요청 `:897`), `apps/api/tests/test_tenant_isolation_full_path.py` |
| 품질 탭 / 비멤버의 요청 | 충족 | `0031:48-51` · 테스트 `test_control_router.py:816` |
| 품질 탭 / 집계할 데이터가 없다 | 충족 | `ControlRoom.tsx:552-556` · 테스트 `ControlRoom.test.tsx:556` 부근의 빈 상태 사례 |

### ai-controls-showcase

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| 전후 증거 / 충돌 판정 비용 누락의 전후 비교 | 충족 | `apps/dashboard/components/ControlledAiShowcase.tsx` · 테스트 `test_controlled_ai_evidence.py:979`, `apps/dashboard/tests/ControlledAiShowcase.test.tsx` |
| 전후 증거 / Step 2 예산 및 단락 시나리오의 전후 비교 | 충족 | 같은 렌더 경로, `apps/dashboard/content/controlled-ai/step1.json` · 테스트 `test_controlled_ai_evidence.py:979` |
| 전후 증거 / Step 3 출력 계약 시나리오의 전후 비교 | 충족 | `test_controlled_ai_evidence.py:848-875`, `:979`, `:996`, `:1008`. 10개 시나리오의 `after.commit`은 `9976b9d`로 HEAD의 조상이고, 그 뒤 변경은 이 JSON뿐이다. `before.commit` `79b68fe`도 HEAD의 조상이며 r4에서 다시 측정하지는 않았다 |
| 전후 증거 / 증거 파일의 내용 검사 | 충족 | 테스트 `test_controlled_ai_evidence.py:1040` |
| 전후 증거 / 아직 구현되지 않은 단계 | 충족 | 테스트 `test_controlled_ai_evidence.py:1022`, `ControlledAiShowcase.test.tsx` |

## 조치가 필요한 항목

1. **충돌 판정이 200 `error`로 성공하지 않음을 확인하는 테스트가 없다** — 근거 Scenario: "공급자가 HTTP 200 본문에 `error`를 담아 돌려준다 ... 충돌 판정이 판정 없이 성공으로 끝나지 않는다". 코드는 맞다(`conflict.py:133`, 실측은 위 표). 그러나 `test_output_contract.py:532`, `:603`은 게이트웨이만 보고, `run_conflict_check`에 `ProviderError`를 통과시키는 테스트는 `test_output_contract.py`, `test_handlers.py`, `test_queue.py`, `test_controlled_ai_evidence.py`, `test_llm_gateway.py` 어디에도 없다. 저장소 밖 복사본에서 `conflict.py:133`을 `except Exception:`으로 바꿔 이 다섯 파일을 돌린 결과 170개 모두 통과했다. 이 절은 사용자 결정 (2)가 재시도를 유지한 이유이므로 회귀를 잡아야 한다. 제안: `test_output_contract.py:242`의 `_ConflictDb`로 200 `error` 응답을 돌려 `ProviderError`가 올라오고 `db.completed == 0`, `db.disputed == []`임을 단언한다. `:603`에 `NON_RETRYABLE_ERRORS` 단언도 더한다. 지금은 `:532`에만 있다.

## 비차단 관찰 (판정에 넣지 않음)

모두 합성 입력으로 재현했고 실제 공급자가 이런 값을 내는지는 확인하지 못했다.

1. **단정이 섞였는데 수리 없이 `resolved`로 저장되는 입력이 남아 있다** — `_ask_with_mode` 실측, 전부 호출 1회, 위반 없음, `resolved`다.
   - `제공된 자료로는 알 수 없습니다. 환불에는 영수증이 필요합니다.` (`_GUIDANCE`의 `필요`, `answer_contract.py:51`)
   - `제공된 자료로는 알 수 없습니다. 7일 안에 신청이 있으면 환불됩니다.` (`있으면`)
   - `- 환불은 7일 안에 됩니다\n- 수수료는 자료에서 찾을 수 없습니다` (마침표 없는 목록은 `split_sentences`가 한 문장으로 본다)
   - `자료에 없습니다\n환불은 7일 안에 됩니다` (같은 원인)
   - `환불은 7일 안에 되지만 수수료는 자료에서 찾을 수 없습니다.` (한 문장 안의 혼합)
   - `자료에서 찾을 수 없으면 관리자에게 문의합니다.` (r3가 고치라고 한 `없으면` 형태가 `자료` 주어로는 남았다)

   위 앞의 네 입력은 "단정 문장과 근거 부족 문장을 함께 담고 인용이 없다"에 문자 그대로 해당한다. 호출자 지시에 따라 판정을 낮추지 않았고, r3도 이 항목의 조건을 지정 문장의 판정으로 한정했다. 다만 이것은 표현을 놓치는 방향이 아니라 인용 없는 단정이 저장되는 방향이다. `answer_contract.py:59`와 `design.md:38`의 "수리 호출 1회가 더 들 뿐"은 이 방향을 설명하지 못한다. 실제 답변에서 이런 형태가 나오는지는 품질 탭이나 다음 재생으로 볼 수 있다.

2. **깨진 사용량의 잔여 입력** — `{"prompt_tokens": 1 뒤에 0 400개}`와 같은 값의 `cost`는 `math.isfinite`(`llm.py:518`, `:532`)가 `OverflowError`를 던져 호출 1회, 기록 0행, 재시도 대상이다(실측). `prompt_tokens: 1e30`과 `cost: 1e300`은 게이트웨이를 통과하지만 `int`, `bigint` 컬럼(`0009_pipeline_ops.sql:121`, `:125`)을 넘는다. 실제 DB에서는 `service.py:786`의 `raise_for_status`로 같은 경로가 될 것으로 보나 실행하지는 않았다.

3. **`출력 위반 → 200 error` 순서** — 실측: 한 번의 실행에서 호출 2회, 기록 2행(`json_invalid`, `provider_error`), `ProviderError`로 끝나 큐가 재시도한다. 계속 이 순서면 `max_attempts` 3에서 모델 출력이 있는 호출이 3회가 된다(계산값). 5xx도 같은 구조다.

4. **표현 놓침** — `제공된 자료만으로는 답변드릴 수 없습니다.`, `제공된 문서에서 답을 찾을 수 없습니다.`, `제공된 근거만으로는 알 수 없습니다.`, `죄송하지만 제공된 자료에는 이 내용이 없습니다.`는 위반으로 세어 수리 호출이 1회 는다(실측). `design.md:38`이 받아들인 방향이다. `답변드릴`은 r3가 제안했으나 반영되지 않았다.

5. **테스트 없는 변경** — `_context_blocks`의 앵커 제거(`ask.py:458-459`, `:465`)에는 테스트가 없다. 대응 Scenario가 없어 지적으로 세지 않았다. 격리 관점 판단은 `tenant-isolation-reviewer` 몫이다.

6. **200 응답의 `error`와 정상 `choices` 공존** — r3와 같다. `_has_provider_error`(`llm.py:483-489`)가 유효한 답을 버리고 `ProviderError`를 던진다. `error: ""`도 같다. 코드로 확인했고 이번에 다시 실측하지는 않았다.

7. **문서** — `design.md:22`의 "`_read_content`의 예외도 기록 뒤에 다시 던진다"와 `design.md:46`의 `BROAD_ANCHOR_PATTERN`은 HEAD와 맞지 않는다(r3와 같음). `docs/ops/ask-sample-replay.md:38`의 "최종 판정 함수를 ... 다시 적용한 값"(0/30)은 확인할 수 없었다. 재생 결과 파일을 찾지 못했고, `_is_abstention`이 바뀐 `9976b9d`에서 표의 수치는 수정되지 않았다.

## 설계 결정 대조

| 결정 | 결과 | 비고 |
| --- | --- | --- |
| D1 기록 후 판정, 예외 없는 분류 | 일치 (관찰 2, 7) | r3의 `usage` 이탈은 닫혔다 |
| D2 펜스 한 겹 | 일치 | 변경 없음 |
| D3 placeholder 전체 일치 | 일치 | 변경 없음 |
| D4 2회와 비재시도 | 일치 | 200 `error`는 `design.md:68`과 스펙의 예외다 |
| D5 두 코드 | 일치 (관찰 1, 4) | 사용자 결정대로 전체 근거 부족만 면제한다 |
| D6 사후 수리와 2,000토큰 초안 | 일치 | `ask.py:618-659`, `:1003-1025` |
| D7 `fallback` 상태와 본문 정리 | 일치 | 표기는 관찰 7 |
| D8 근거 테이블과 범위 교체 | 일치 | 변경 없음 |
| D9 품질 집계 형태와 타입 확인 | 일치 | 변경 없음 |

## 수정으로 깨진 시나리오 확인

찾지 못했다. 아래를 각각 확인했다.

- `_is_abstention`: 시드 문구(`0006`의 "제공된 자료로는 알 수 없습니다")와 안내 한 문장이 붙은 형태, 제목이 붙은 형태가 호출 1회로 통과한다.
- `resolve_citations`의 `else` 분기는 상한까지 안정되지 않을 때만 돈다. 얕은 중첩과 정상 앵커는 그대로다(`test_ask_citations.py:48-53`).
- `neutralize_anchor_brackets`: Fallback 시나리오와 짝수·홀수 괄호 모두 앵커가 남지 않는다(`test_answer_contract.py:165`, `:173`, `:178`).
- `token_count`, `cost_micros`: 정상 값의 기록이 그대로다(`test_output_contract.py:111`, `test_llm_gateway.py`). `record_stream_usage`도 같은 함수를 쓴다(`apps/worker/src/worker/llm_gateway.py:196-198`).
- `_has_provider_error`: `choices[0].error`도 소진으로 세지 않고 `exhausted`가 서지 않는다(`llm.py:315-319`, 실측).
- 스펙 변경: `openspec validate`를 통과하고, 새 문구가 `design.md`의 사용자 결정 두 건과 맞는다.

## 검증 실행

- `uv run pytest` (worker 6개, api 4개 파일, `packages/core/tests`): 493 passed. 실패가 없어 단독 재실행은 필요 없었다. 전체 저장소 테스트는 돌리지 않았다. 호출자가 전한 989 passed, 471 passed는 다시 확인하지 않았다.
- `pnpm exec vitest run` (`ControlRoom`, `ControlledAiShowcase`, `AskThreadHistoryRestore`, `AskConversation`): 39 passed. `tsc --noEmit`: 오류 출력 없음.
- `uv run ruff check` (api, worker, core의 `src`): 통과. `openspec validate ai-control-output-contract --strict`: valid.
- `supabase/tests/wiki_page_evidence.sql`을 `docker exec psql`로 실행: 오류 없이 ROLLBACK까지 진행. `supabase test db`는 실행하지 않았다.
- 변이 확인은 `git archive HEAD`로 만든 저장소 밖 복사본을 `PYTHONPATH`로 앞세워 돌렸다. `conflict.py`를 `except Exception:`으로 바꾼 worker 5개 파일은 170 passed(가드 없음), `control.py`의 `missing_content` 키를 바꾼 품질 테스트는 1 failed(가드 있음)다.
- "실측"은 HEAD 코드에 합성 입력을 넣어 재현한 것이며 임시 파일은 저장소 밖에 두었다. 실제 LLM 재생은 돌리지 않았다.

## 판정 근거

Scenario의 동작은 모두 구현됐고 r3 지적 3건도 닫혔다. 그래도 `pass`가 아닌 이유는 새 Scenario의 THEN 한 절을 확인하는 테스트가 없고, 변이로 그 부재를 확인했기 때문이다. 이는 r3 항목 3과 같은 성격(코드는 맞고 회귀를 잡을 테스트가 없음)이고 가상의 입력이나 새 요구가 아니다. 스펙을 고칠 필요가 없고 테스트만 더하면 되므로 등급은 `needs_fix`다.

게이트 상한 3라운드는 이미 지났고 r4는 사용자가 한 번 더 승인한 라운드다. 따라서 r5를 자동으로 열지 않는다. 테스트를 더한 뒤 재리뷰를 열지, 재리뷰 없이 PR로 갈지는 사용자가 정한다. 관찰 1을 위험으로 받아들일지도 함께 정하는 것이 좋다.

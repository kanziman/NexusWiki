# Spec Conformance 리뷰 — ai-control-output-contract r5

- 판정: pass
- 대상: `git diff 45ec35b..be10cef` (`be10cef9870222c4e1f95ccafe1124a4d644082e`). 사용자가 승인한 좁은 범위라 change 전체를 다시 보지 않았다
- 일시: 2026-11-03T07:35:09+09:00

## 요약

r4 지적 1건은 해결됐다. 근거 부족 판정 관찰(r4 관찰 1)의 입력 6개도 모두 위반으로 잡힌다.

시드 문구와 실제 모델의 근거 부족 답변은 정상 면제된다. 다만 이 diff로 면제 범위가 크게 좁아졌다. `제공된 자료로는 이 질문에 답할 수 없습니다.`처럼 Scenario WHEN에 해당하는 표현도 이제 수리 호출을 탄다. `design.md` D5가 받아들인 방향이고 데이터를 망가뜨리지 않아 차단으로 올리지 않았지만, 이 판단은 D5에 기대므로 사람이 확인하기를 권한다(관찰 1).

## r4 대조

| 항목 | 결과 | 증거 |
| --- | --- | --- |
| 지적 1: 충돌 판정의 200 `error` 테스트 | 해결 | 테스트 `apps/worker/tests/test_output_contract.py:626`. `ProviderError`가 올라오고 `db.completed == 0`, `db.disputed == []`를 단언한다. 저장소 밖 복사본에서 `conflict.py:133`을 `except Exception:`으로 바꾸면 이 테스트가 실패한다(r4에서는 170개 전부 통과). `:603`에 `NON_RETRYABLE_ERRORS` 단언을 더하자는 r4 제안은 반영되지 않았다(관찰 4) |
| 관찰 1: 단정이 섞였는데 면제되는 입력 | 해결 | `packages/core/src/nexuswiki_core/answer_contract.py:45-56`, `:69-78`. r4의 6개 입력을 `_ask_with_mode`로 돌렸다. 전부 호출 2회, 위반 `no_citation`, 수리 후 `resolved`다. 테스트는 `packages/core/tests/test_answer_contract.py:161` 부근. 같은 부류의 잔여 입력은 관찰 2 |
| 관찰 2: 깨진 사용량의 잔여 입력 | 일부 해결 | `apps/worker/src/worker/llm.py:521-526`, `:538-542`. `prompt_tokens`와 `cost`가 `10**400`일 때 정상 출력은 호출 1회·1행, 깨진 출력은 호출 2회·2행에 `LlmSchemaError`다(실측). 테스트 `test_output_contract.py:620`. `cost: 1e300`은 남았다(관찰 3) |
| 관찰 5: `_context_blocks` 앵커 제거 테스트 | 해결 | 테스트 `apps/api/tests/test_ask_citations.py:65` |

## 시나리오 판정

diff가 닿는 Scenario만 적었다. 나머지(placeholder, 펜스, 페이지 근거 청크, 기록 재열람)는 diff가 코드 경로를 건드리지 않는다.

### grounded-answering

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| Ask 인용 계약과 수리 / 근거 부족을 밝힌 답변 | 충족 (관찰 1) | `answer_contract.py:45-51`, `:69-78` · 테스트 `apps/api/tests/test_ask_router.py:1084`, `test_answer_contract.py:66-71`. 시드 문구, 스펙 문구(`제공된 자료로 답할 수 없습니다.`), 재생 파일의 실제 답변 3건을 Ask 경로로 돌렸다. 전부 호출 1회, 위반 없음, `resolved`다 |
| Ask 인용 계약과 수리 / 단정과 근거 부족이 섞인 답변 | 충족 (관찰 2) | `answer_contract.py:76-78` · 테스트 `test_answer_contract.py:161` 부근. 실측은 위 r4 대조와 같다 |
| Ask 인용 계약과 수리 / 인용이 하나도 없는 답변을 수리한다 | 충족 | 테스트 `test_ask_router.py:1061` 통과. 변경된 판정에서도 인용 없는 일반 답변은 위반이다 |
| Ask 인용 계약과 수리 / 정상 답변 | 충족 | `answer_contract.py:91`. 인용이 있으면 `_is_abstention`을 평가하지 않아 이 diff의 영향이 없다 |
| 결정론적 Ask Fallback / 수리도 실패한다, 수리 호출 자체가 실패한다 | 충족 | `apps/api/src/api/services/ask.py:1003-1032` (변경 없음) · 테스트 `test_ask_router.py:1095` 통과 |
| 결정론적 Ask Fallback / 근거 본문에 앵커 문법이 들어 있다 | 충족 | 테스트 `test_answer_contract.py:190`이 깊이와 괄호 수를 넓혀 통과한다. `test_ask_citations.py:65`도 통과 |
| 품질 통제 모드 / shadow, off | 충족 | `ask.py:994` (변경 없음) · 테스트 `test_ask_router.py:1119`, `:1127` 통과. shadow의 위반 수는 관찰 1만큼 늘 수 있다 |

### wiki-compilation

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| 호출 상한 / 어떤 입력에도 호출은 2회를 넘지 않는다 | 충족 (관찰 3) | `llm.py:521-526`, `:538-542` · 테스트 `test_output_contract.py:620`, 위 실측. 이 값들은 `_Sink`로 쟀고 실제 DB에 넣지는 않았다 |
| 호출 상한 / HTTP 200 본문의 공급자 오류 | 충족 | 테스트 `test_output_contract.py:626`, `:603`, `:532`. r4의 부분 충족이 닫혔다 |
| 호출 상한 / 파싱할 수 없는 출력의 재시도 | 충족 | `llm.py`의 재시도 경로 변경 없음. 관련 테스트 통과 |
| 충돌 판정 쌍 격리 / 한 쌍만 스키마를 어긴다 | 충족 | `conflict.py:133` 변경 없음 · 테스트 `test_output_contract.py:242`, `:424` 통과 |

`design.md`의 Goals 변경("모델 응답 기준")은 스펙의 호출 상한 문구와 맞는다.

## 조치가 필요한 항목

없다.

## 비차단 관찰 (판정에 넣지 않음)

재생 파일에 든 답변 말고는 모두 내가 만든 합성 입력이다. 실제 모델이 이 표현을 얼마나 내는지는 확인하지 못했다.

1. **근거 부족 면제가 크게 좁아졌다 (이 diff가 만든 변화)** — `45ec35b`와 `be10cef`의 `_is_abstention`을 같은 입력에 돌렸다. 근거 부족만 밝히는 입력 42개 중 이전에는 39개가 면제됐고, 지금은 16개가 면제된다. 면제에서 빠진 23개의 예는 다음과 같다.
   - 표현 변형: `제공된 자료로는 이 질문에 답할 수 없습니다.`, `제공된 자료에서 관련 정보를 찾을 수 없습니다.`, `제공된 자료만으로는 정확히 알 수 없습니다.`, `죄송하지만 제공된 자료로는 알 수 없습니다.`
   - 서식: `**제공된 자료로는 알 수 없습니다.**`, `- 제공된 자료로는 알 수 없습니다.`, `**핵심 답변**\n\n제공된 자료로는 알 수 없습니다.`
   - 안내 문장: `제공된 자료로는 알 수 없습니다. 2025년 재무제표가 필요합니다.` `supabase/migrations/0006_seed_prompts.sql:151`이 지시한 형태("무엇이 있어야 답할 수 있는지 한 줄")이지만 `_GUIDANCE`(`answer_contract.py:53-56`)에 걸리지 않는다. `환불에는 영수증이 필요합니다.`와 정규식으로 구분하기 어려운 형태다

   이 가운데 4개(`이 질문에 답할`, `관련 정보를 찾을`, 굵은 글씨, `2025년 재무제표`)를 Ask 경로로 돌렸다. 전부 호출 2회, 위반 `no_citation`이다. 수리 호출이 시드 문구를 돌려주면 `resolved`, 같은 표현을 되풀이하면 `fallback`이다. 따라서 `design.md:38`과 `answer_contract.py:66`의 "수리 호출 1회가 더 들 뿐"은 전부를 설명하지 못한다. 정직한 근거 부족 답변이 근거 목록으로 바뀔 수 있다.

   차단으로 올리지 않은 근거는 세 가지다. D5가 이 방향을 받아들였고(r4 관찰 4도 같은 판단), 인용 없는 단정이 저장되는 방향이 아니며, `repair_instruction`(`answer_contract.py:111-112`)이 면제되는 문구를 직접 지시한다. 재생 파일 `before`, `after`, `step3`의 근거 부족 답변 3건도 모두 면제된다. 다만 세 건 모두 같은 질문(`q30`)의 답이라 표본이 작고, `경영진 요약` 템플릿(`0006:184`, 굵은 `**결론**` 구조)으로 재생했는지는 확인하지 않았다. `shadow` 또는 품질 탭의 `no_citation` 수로 운영에서 볼 수 있다. 줄이려면 서식 문자 제거와 `자료…` 뒤 목적어 한 구 허용을 검토할 수 있으나, 이것은 새 요구가 아니라 선택지다.

2. **단정이 섞였는데 면제되는 입력이 아직 있다** — `_GUIDANCE`가 부분 일치라 안내 표현이 들어 있으면 단정도 통과한다. 앞의 두 입력은 Ask 경로에서 호출 1회, 위반 없음, `resolved`다. 나머지는 판정 함수만 돌렸다.
   - `제공된 자료로는 알 수 없습니다. 고객 정보가 필요하며 환불은 7일 안에 됩니다.`
   - `제공된 자료로는 알 수 없습니다. 환불은 7일 안에 되며 이를 확인하려면 영수증을 보면 됩니다.`
   - `제공된 자료로는 알 수 없습니다. 영수증이 있어야 확인 후 환불됩니다.`
   - `제공된 자료로는 알 수 없습니다. 환불 문서를 제공합니다.` (`45ec35b`에서는 위반이었고 이 diff로 면제됐다)

   Scenario "단정과 근거 부족이 섞인 답변"의 WHEN에 문자 그대로 해당하고 인용 없는 단정이 저장되는 방향이다. 다만 안내 표현과 단정이 한 문장에 겹쳐야 하는 입력이라 r4의 6개보다 좁다.

3. **`cost: 1e300`은 아직 지나간다** — `cost_micros`에는 토큰과 달리 상한이 없어 약 `10**306` 정수를 싱크로 넘긴다(실측). 로컬 DB에서 `select (1e306)::bigint`는 `bigint out of range`다. `usage_events` 저장 전체를 실행하지는 않았다. 저장이 실패하면 기록과 호출 상한을 벗어나는 경로일 수 있어 스펙의 "깨진 사용량 값" 문구에 닿는다. 한편 `llm.py:67`의 주석은 `bigint`라고 하지만 토큰 컬럼은 `int`다(`0009_pipeline_ops.sql:121-123`). 상한 값 `2**31 - 1`은 `int`에 맞다.

4. **테스트 범위** — `test_output_contract.py:626`은 최상위 `error`만 쓴다. `choices[0].error`의 충돌 판정 경로와 `:603`, `:626`의 `NON_RETRYABLE_ERRORS` 단언은 없다(`LlmSchemaError` 여부만 본다). 재시도 분류 단언은 `:546`에 있다. `:626`의 변이 확인은 통과했으므로 차단할 사유는 아니다.

## 판정 근거

r4 지적은 변이로 확인할 수 있게 닫혔고, diff가 깨뜨린 필수 경로는 찾지 못했다. 면제가 좁아진 관찰 1은 Scenario의 WHEN에 해당하는 일부 표현에서 THEN이 나오지 않는 것이지만, D5가 비용으로 받아들인 방향이고 실패 결과도 안전한 쪽이다. 호출자 지시대로 차단할 만한 것만 올리면 `pass`가 맞다. D5를 다른 뜻으로 읽어 "표현 놓침은 허용하되 면제 범위가 이만큼 줄어드는 것은 아니다"로 본다면 이 항목은 `needs_fix`가 된다. 그 해석은 사용자가 정한다.

## 검증 실행

- `uv run pytest` (`test_answer_contract.py`, `test_ask_citations.py`, `test_output_contract.py`, `test_ask_router.py`, `test_llm_gateway.py`, `test_handlers.py`): 228 passed
- `uv run ruff check` (api, worker, core의 `src`): 통과. `openspec validate ai-control-output-contract --strict`: valid
- 실행하지 않은 것: 저장소 전체 테스트, dashboard 테스트(diff에 dashboard 변경 없음), 타입 검사, 실제 LLM 재생, `usage_events` 실제 저장
- "실측"은 `be10cef` 코드에 합성 입력을 넣은 것이다. 임시 파일과 변이 복사본은 저장소 밖에 두었다

# Spec Conformance 리뷰 — ai-control-output-contract r3

- 판정: blocked
- 대상: `git diff feat/ai-context-budget..HEAD` (`03dbad2da396da8a7c2722d73761dc6815a64c38`, 스택된 브랜치라 main이 아니라 이 범위로 봤다). r2 이후 변경은 `7bbe687`, `03dbad2`이다
- 일시: 2026-11-03T06:50:00+09:00

## 요약

r2 지적 5건 중 2건(3, 5)은 해결됐고, 1건(4)은 코드가 해결됐지만 양수 집계를 단언하는 테스트가 없으며, 2건(1, 2)은 일부만 해결됐다. Scenario 27개 중 충족 24개, 부분 충족 3개, 미충족 0개다. 남은 지적은 스펙을 고치지 않고 코드와 테스트로 해결할 수 있다. 그래도 리뷰 게이트의 3라운드 상한(`.claude/CLAUDE.md` 「리뷰 게이트」)에 따라 `pass`가 아니므로 `blocked`로 확정하고 사람에게 넘긴다.

## r2 지적 대조

| # | r2 지적 | 결과 | 증거 |
| --- | --- | --- | --- |
| 1 | 근거 부족 판정의 과대 일치 | 일부 해결 | `없습니다` 단독 대안이 빠져 `문서 업로드 용량에는 제한이 없습니다.`는 이제 수리된다(실측 호출 2회). r2가 적은 `문서를 찾을 수 없으면 관리자에게 문의합니다.`는 그대로 통과한다. 조치 항목 1 |
| 2 | 깨진 200 응답이 호출 상한 밖으로 빠진다 | 일부 해결 | r2가 적은 입력은 해결됐다(`apps/worker/src/worker/llm.py:281-284`, `:491-492`, 테스트 `apps/worker/tests/test_output_contract.py:511`). `usage` 안의 깨진 값이 같은 경로로 남았다. 조치 항목 2 |
| 3 | `stack.md` 기록과 `314a855` 설명 | 해결 | `docs/reference/stack.md:50`, `docs/ops/ask-sample-replay.md:21`, `:36`, `:38` |
| 4 | `missing_content` 미집계 | 코드 해결, 테스트 부족 | `supabase/migrations/0031_control_quality_tab.sql:32`, `:95`, `:127`, `apps/api/src/api/routers/control.py:586`, `apps/dashboard/components/ControlRoom.tsx:601`. 조치 항목 3 |
| 5 | 앵커 결합 placeholder 테스트 없음 | 해결 | 테스트 `test_output_contract.py:495`. 앵커 제거를 무력화하면 입력 3개가 모두 통과하는 것을 실측했으므로 이 테스트는 회귀를 잡는다. `{{title}} [[src:s1]]`은 매개변수에 없지만 실측으로 제목과 본문 모두 거부된다 |

## 시나리오 판정

### grounded-answering

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| Ask 인용 계약과 수리 / 인용이 하나도 없는 답변을 수리한다 | 부분 충족 | 수리 경로는 충족한다 (`apps/api/src/api/services/ask.py:991-1020`, 테스트 `apps/api/tests/test_ask_router.py:1061`). 일부 인용 없는 답변이 수리 없이 `resolved`로 저장된다 (조치 항목 1) |
| Ask 인용 계약과 수리 / 근거 부족을 밝힌 답변 | 부분 충족 | 시드 문구는 통과한다 (`packages/core/src/nexuswiki_core/answer_contract.py:44-49`, 테스트 `test_ask_router.py:1084`, `packages/core/tests/test_answer_contract.py:68`). `제공된 자료로는 답변할 수 없습니다.`는 위반이 되어 수리를 부른다 (조치 항목 1) |
| Ask 인용 계약과 수리 / 정상 답변 | 충족 | `answer_contract.py:52-64` · 테스트 `test_ask_router.py:1046`, `test_answer_contract.py:78` |
| 결정론적 Ask Fallback / 수리도 실패한다 | 충족 | `ask.py:1009-1020`, `answer_contract.py:95-130` · 테스트 `test_ask_router.py:1095`, `test_answer_contract.py:89` |
| 결정론적 Ask Fallback / 수리 호출 자체가 실패한다 | 충족 | `ask.py:641-643` · 테스트 `test_ask_router.py:1095`, `:1134`, `:1143` |
| 결정론적 Ask Fallback / 근거 본문에 앵커 문법이 들어 있다 | 충족 | `answer_contract.py:87-92`, `:113-116`, `packages/core/src/nexuswiki_core/citations.py:50-55` · 테스트 `test_answer_contract.py:89`, `:103`, `:157`, `:165`. 반복 상한을 넘는 중첩도 실측으로 앵커가 남지 않는다 |
| 결정론적 Ask Fallback / 기록을 다시 연다 | 충족 | `apps/dashboard/components/AskConversation.tsx:49`, `:129`, `:689` · 테스트 `apps/dashboard/tests/AskThreadHistoryRestore.test.tsx:182`. 근거 목록 본문까지 단언하지는 않는다 |
| 품질 통제 모드 / shadow 모드의 위반 | 충족 | `ask.py:982-991` · 테스트 `test_ask_router.py:1119` |
| 품질 통제 모드 / off 모드 | 충족 | `ask.py:982` · 테스트 `test_ask_router.py:1127` |

### wiki-compilation

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| 코드 펜스와 의미 검증 / 펜스로 감싼 정상 JSON | 충족 | `llm.py`의 `parse_json_only` · 테스트 `test_output_contract.py:111`, `apps/worker/tests/test_controlled_ai_evidence.py`의 `compile_fence_retry` |
| 코드 펜스와 의미 검증 / placeholder 페이지 | 충족 | `apps/worker/src/worker/handlers/compile.py:65-75`, `:105` · 테스트 `test_output_contract.py:175`, `:495` |
| 코드 펜스와 의미 검증 / 본문이 템플릿 문법을 설명한다 | 충족 | `compile.py:59-61`. 값 반환으로 바뀐 뒤에도 `{{variable}}`이 보존된다 (실측) · 테스트 `test_output_contract.py:187` |
| 호출 상한 / 어떤 입력에도 호출은 2회를 넘지 않는다 | 부분 충족 | 스키마 위반, 내용 없는 응답, 깨진 본문은 2회로 끝난다 (`llm.py:281-298`, 테스트 `test_output_contract.py:125`, `:369`, `:511`). `usage`의 깨진 값은 비용 기록 없이 큐로 빠진다 (조치 항목 2). 200 `error` 본문은 「사람 확인 사항」 참조 |
| 호출 상한 / 파싱할 수 없는 출력의 재시도 | 충족 | `llm.py:545-555` · 테스트 `test_output_contract.py:145`, `:156`, `:443` |
| 페이지 근거 청크 / 발급되지 않은 앵커 | 충족 | `compile.py:171`, `:180`, `:287`, `:440-451` · 테스트 `test_output_contract.py:343`, `:416`, `:460` |
| 페이지 근거 청크 / 재컴파일 | 충족 | `supabase/migrations/0030_wiki_page_evidence.sql:68-80` · 테스트 `supabase/tests/wiki_page_evidence.sql` (직접 실행 통과). 핸들러를 두 번 도는 테스트는 없다 |
| 페이지 근거 청크 / 다른 워크스페이스 사용자의 조회 | 충족 | `0030:43-48` · 테스트 `supabase/tests/wiki_page_evidence.sql` (직접 실행 통과) |
| 충돌 판정 쌍 격리 / 한 쌍만 스키마를 어긴다 | 충족 | `apps/worker/src/worker/handlers/conflict.py:125-135`. `LlmSchemaError`만 잡으므로 `ProviderError`는 큐로 간다 · 테스트 `test_output_contract.py:242`, `:424` |

### ai-control-room

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| 품질 탭 / editor가 품질 탭을 연다 | 충족 | `control.py:544-597`, `0031`, `ControlRoom.tsx:549-614` · 테스트 `apps/api/tests/test_control_router.py:816`, `apps/dashboard/tests/ControlRoom.test.tsx:452`. `missing_content` 양수 집계는 롤백 트랜잭션 실측으로만 확인했다 (조치 항목 3) |
| 품질 탭 / viewer가 품질 탭을 연다 | 충족 | `control.py`의 `can_view` 분기, `0031` · 테스트 `test_control_router.py:912-915`, `apps/api/tests/test_tenant_isolation_full_path.py` |
| 품질 탭 / 비멤버의 요청 | 충족 | `0031:48-51` · 테스트 `test_control_router.py:888` |
| 품질 탭 / 집계할 데이터가 없다 | 충족 | `ControlRoom.tsx:552-556` · 테스트 `ControlRoom.test.tsx`의 빈 상태 사례 (`missing_content: 0`, `:556`) |

### ai-controls-showcase

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| 전후 증거 / 충돌 판정 비용 누락의 전후 비교 | 충족 | `apps/dashboard/components/ControlledAiShowcase.tsx` · 테스트 `test_controlled_ai_evidence.py:979`, `apps/dashboard/tests/ControlledAiShowcase.test.tsx` |
| 전후 증거 / Step 2 예산 및 단락 시나리오의 전후 비교 | 충족 | 같은 렌더 경로, `apps/dashboard/content/controlled-ai/step1.json` · 테스트 `test_controlled_ai_evidence.py:979` |
| 전후 증거 / Step 3 출력 계약 시나리오의 전후 비교 | 충족 | `test_controlled_ai_evidence.py:848-875`, `:979`, `:1008`. 10개 시나리오의 `after.commit`은 `7bbe687`이고 HEAD의 조상이다. `before.commit`은 `79b68fe`이며 r3에서 다시 측정하지는 않았다 |
| 전후 증거 / 증거 파일의 내용 검사 | 충족 | 테스트 `test_controlled_ai_evidence.py:1040` |
| 전후 증거 / 아직 구현되지 않은 단계 | 충족 | 테스트 `test_controlled_ai_evidence.py:1022`, `ControlledAiShowcase.test.tsx` |

## 조치가 필요한 항목

1. **근거 부족 판정이 양쪽으로 어긋난다** (r2 항목 1의 잔여) — `answer_contract.py:45-46`의 첫 대안과 `:48`의 `근거가 없습니다`가 문맥을 보지 않고, 답변 어디에든 일치하면 답변 전체를 통과시킨다. `_ask_with_mode`로 Ask 경로를 실측했다.

   과대 일치(수리 없이 `resolved`, 호출 1회, 위반 `[]`):
   - `문서를 찾을 수 없으면 관리자에게 문의합니다.` (r2가 적은 문장)
   - `환불을 거부할 근거가 없습니다.`
   - `반품은 3일 안에 가능합니다. 수수료는 5천원입니다. 다만 배송비는 자료에서 찾을 수 없습니다.`

   셋째가 가장 무겁다. 근거 없는 단정 두 문장이 끝에 붙은 한 문장 때문에 인용 없이 저장된다. 근거: "답변이 있는데 해소된 인용이 하나도 없으면 위반이다", design Goals "인용 없는 답변의 `resolved` 저장 차단". D5가 허용한 것은 표현을 놓치는 방향뿐이다.

   놓침:
   - `제공된 자료로는 답변할 수 없습니다.`: `no_citation`, 호출 2회. 정규식의 `답할`이 `답변할`에 일치하지 않는다. 수리도 같은 문장을 내면 `fallback`으로 끝난다(실측). r2가 양성 사례로 제안한 문장이다.

   근거: "근거 부족을 밝히고 인용이 없는 답변은 위반이 MUST NOT 된다", D5는 이 놓침의 비용을 수리 1회로 설명하지만, 수리가 같은 문장을 내면 정직한 답변이 `fallback`이 되므로 그 설명보다 결과가 크다. 다만 수리 지시가 시드 문구를 알려 주므로(`answer_contract.py:83`) 실제 모델이 얼마나 반복할지는 측정하지 않았다.

   제안: 표현이 문장 끝에 오는 경우만 인정해 `없으면`, `없는 경우`, `없으니`를 걸러 낸다. `답변할`과 `답변드릴`을 대안에 넣는다. 답변 전체가 짧을 때만 인정하거나 앞에 단정 문장이 있으면 위반으로 보는 조건을 둔다. `근거가 없습니다`는 `관련 근거가`처럼 대상을 고정한다. 위 문장들을 `test_answer_contract.py:68`, `:151`의 매개변수에 넣는다. 일반 답변에 대한 정규식의 정확도에는 한계가 있으므로 이 항목의 조건은 위 문장들의 판정이다.

2. **`usage`의 깨진 값이 호출 상한과 비용 기록을 빠져나간다** (r2 항목 2의 잔여) — `_read_usage`(`llm.py:472-480`)는 `usage`가 dict인지만 본다. 기록 인자의 `int(usage.get("prompt_tokens") or 0)`(`:305-307`)과 `cost_micros`(`:308`)가 `on_attempt`를 부르기 전에 던진다. 게이트웨이로 실측했다.
   - `usage: {"prompt_tokens": "abc"}`: 호출 1회, 기록 0행, `ValueError`, 비재시도 아님.
   - `usage: {"prompt_tokens": [1]}`: 호출 1회, 기록 0행, `TypeError`, 비재시도 아님.
   - `usage: {"cost": 1e999}`: 호출 1회, 기록 0행, `OverflowError`, 비재시도 아님.

   `apps/worker/src/worker/queue.py:296-311`은 이 예외들을 `fail_job`으로 보내고 `max_attempts` 기본값은 3이다(`supabase/migrations/0003_jobs.sql:48`). 계속 이런 응답이면 잡 하나가 3회 호출하고 비용은 한 행도 남지 않는다. 실제 큐를 돌린 값이 아니라 계산한 값이다. 공급자가 실제로 이런 값을 보내는지는 확인하지 못했다. 근거 Scenario: "어떤 입력에도 호출은 2회를 넘지 않는다 ... 두 호출의 비용이 모두 기록되며". D1: "분류 함수가 던지면 지불한 비용이 사라지므로". 제안: 토큰을 안전하게 정수로 바꾸는 함수를 두고 숫자로 바꿀 수 없는 값은 0으로 처리하며, `cost_micros`는 유한값만 받는다. 세 입력의 호출 수와 기록 행 수를 `test_output_contract.py:511`에 추가한다.

3. **`missing_content` 양수 집계를 잡는 테스트가 없다** (r2 항목 4의 잔여) — `test_control_router.py:905`는 `missing_content`가 없는 시드로 0만 단언하고(시드 `:869-873`), `ControlRoom.test.tsx:496`은 라벨만 본다. `0031:95`의 필터나 `control.py:586`의 키가 틀려도 API 테스트는 통과한다(`count`가 없는 키를 0으로 돌린다). 코드는 맞다. 로컬 DB에서 롤백 트랜잭션으로 행 3개(`missing_content` 2, `provider_error` 1)를 넣어 실측한 결과 `structured_calls = 3`, `structured_missing_content = 2`, `structured_exhausted = 1`이었다. 제안: 시드에 `missing_content` 행을 추가해 1을 단언하고, 대시보드 테스트에서 `3건`을 단언한다.

## 사람 확인 사항

**HTTP 200의 `error` 본문을 호출 상한 밖에 둔 해석** — 실측: 호출 1회, 기록 1행(`provider_error`), `ProviderError`, 재시도 대상. 계속 이 응답이면 잡 하나가 3회 호출한다(계산값). 스펙 Scenario는 "어떤 입력에도", "공급자가 계속 잘못된 응답을 돌려준다", "잡은 재시도 없이"이고 Requirement는 "한 작업의 공급자 호출은 ... MUST 2회"다. 구현의 근거는 스펙이 아니라 `design.md:68`의 "호출 상한의 대상이 아니다"다. 5xx와 전송 실패를 r1, r2에서 "잘못된 응답"으로 세지 않은 것과 일관되고, `conflict.py`가 판정 없이 성공으로 끝나는 것을 막는 타당한 이유도 있어 이 라운드에서는 위반으로 세지 않았다. 다만 r2 참고 사항의 동작을 뒤집은 결정이며 스펙 문구와의 관계는 사람이 판단할 일이다. 스펙에 맞추려면 Scenario를 "모델 출력이 있는 응답"으로 한정하는 스펙 수정이 필요하다.

## 설계 결정 대조

| 결정 | 결과 | 비고 |
| --- | --- | --- |
| D1 기록 후 판정, 예외 없는 분류 | 부분 일치 | `usage`의 깨진 값이 기록 앞에서 나간다 (항목 2). "`_read_content`의 예외도 기록 뒤에 다시 던진다"(`design.md:22`)는 여전히 HEAD와 맞지 않는다. 지금은 위반 코드로 바꾼다 |
| D2 펜스 한 겹 | 일치 | 변경 없음 |
| D3 placeholder 전체 일치 | 일치 | `compile.py:72-74` |
| D4 2회와 비재시도 | 부분 일치 | 항목 2. 200 `error` 본문은 `design.md:68`의 예외다 |
| D5 두 코드 | 불일치 | 표현 판정이 "놓치는 방향"을 넘어 과대 일치한다 (항목 1) |
| D6 사후 수리와 2,000토큰 초안 | 일치 | `ask.py:606-643`, `:991-1020` |
| D7 `fallback` 상태와 본문 정리 | 일치 | `design.md:46`의 `BROAD_ANCHOR_PATTERN` 표기는 옛 이름이다. 실제는 `strip_forged_anchors`다 |
| D8 근거 테이블과 범위 교체 | 일치 | 변경 없음 |
| D9 품질 집계 형태와 타입 확인 | 일치 | `0031:56-75` |

## 수정으로 깨진 시나리오 확인

- 찾지 못했다. 아래 변경을 각각 확인했다.
- `_clean_text`가 값을 바꾸게 된 것: 일반 본문의 `{{variable}}`이 보존되고 공백·placeholder·앵커 결합 입력은 제목과 본문 모두 거부된다 (실측 14건).
- 판정 정규식을 좁힌 것: 기존 양성 문장과 시드 문구는 통과한다 (`test_answer_contract.py:68`). 놓침은 이미 있던 것이고 수정이 만든 것은 아니다 (조치 항목 1).
- 200 `error` 분기: 위반 집계에 넣지 않고 `exhausted`도 세우지 않는다 (`llm.py:314-318`). 실측에서 `provider_error` 행은 호출 수에만 들어갔다.
- `strip_forged_anchors`의 반복 상한: 깊이 1~20에서 앵커가 남지 않았다. Fallback 시나리오는 유지된다.

## 검증 실행

- `uv run pytest` (worker 6개, api 4개 파일, `packages/core/tests`): 478 passed. 실패가 없어 단독 재실행은 필요 없었다. 전체 저장소 테스트는 돌리지 않았다.
- `pnpm exec vitest run` (`ControlRoom`, `ControlledAiShowcase`, `AskThreadHistoryRestore`, `AskConversation`): 39 passed. `tsc --noEmit`: 오류 없음.
- `uv run ruff check` (api, worker, core의 `src`): 통과. `openspec validate ai-control-output-contract --strict`: valid.
- `supabase/tests/wiki_page_evidence.sql`을 `docker exec psql`로 실행: 오류 없이 ROLLBACK까지 진행. `supabase test db`는 실행하지 않았다.
- 로컬 `control_quality_snapshot`의 반환 컬럼에 `structured_missing_content`가 있다. 0031만 적용된 깨끗한 스택에서의 결과는 확인하지 못했다.
- 위 "실측"은 HEAD 코드에 합성 입력을 넣어 재현한 것이며 임시 스크립트는 저장소 밖에 두었다. 실제 LLM 재생은 돌리지 않았다.
- `docs/ops/ask-sample-replay.md:38`의 "최종 판정 함수를 저장된 답변에 다시 적용한 값"은 확인할 수 없었다. 저장된 답변 파일을 저장소와 `/tmp`에서 찾지 못했다.

## 참고 (판정에 넣지 않음)

- `resolve_citations`는 재렌더 횟수만 제한하고 `strip_forged_anchors`와 달리 괄호를 끊지 않는다(`apps/api/src/api/services/ask.py:265`). 실측: 깊이 9 이상의 중첩이면 `rendered_text`에 미발급 앵커가 남는다. 이때 `fabricated_anchor_count`가 1 이상이라 `enforce`에서는 수리나 Fallback으로 가지만 `shadow`와 `off`에서는 그대로 저장된다. 이를 금지하는 Scenario가 없어 지적으로 세지 않았다. 격리 관점 판단은 `tenant-isolation-reviewer` 몫이다.
- 200 응답에 `error`와 정상 `choices`가 함께 있으면 비용을 기록한 뒤 유효한 답을 버리고 `ProviderError`를 던진다. `error: ""`도 같다(실측). 공급자가 실제로 이런 본문을 보내는지는 확인하지 못했다.
- 깨진 본문(HTML, 객체가 아닌 JSON)은 사용량을 읽을 수 없어 `cost_micros = 0`으로 기록된다(실측). 행은 2개 남고 값을 지어내지 않는다.
- 수리 호출 비용은 r2와 같이 코드 경로로만 확인했고 경계까지 통과시키는 테스트는 없다.

## 판정 근거

부분 충족이 3건 남아 `pass`가 아니다. 인용 없는 단정이 근거 부족 한 문장 때문에 `resolved`로 저장되는 경로는 Core Value와 직결되고, 호출 상한은 `usage` 값 하나로 비용 기록 없이 빠져나간다. 지적 자체는 모두 코드와 테스트만 고치면 되므로 성격은 `needs_fix`다. 그러나 이번이 게이트의 마지막 라운드이고 규칙이 "3라운드에서도 `pass`가 아니면 `blocked`으로 확정"이므로 `blocked`로 판정한다. 사람이 정할 것은 세 가지다. 조치 항목 1~3을 고친 뒤 게이트를 한 번 더 열지, 항목 1의 정규식 한계와 항목 2의 입력 희소성을 위험으로 받아들이고 진행할지, 200 `error` 본문의 해석에 맞춰 스펙 문구를 고칠지다.

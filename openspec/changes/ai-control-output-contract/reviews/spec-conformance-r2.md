# Spec Conformance 리뷰 — ai-control-output-contract r2

- 판정: needs_fix
- 대상: `git diff feat/ai-context-budget..HEAD` (`7700bd862f5a4f375249992a5d84c79f47263fda`, 스택된 브랜치라 main이 아니라 이 범위로 봤다). r1 이후 변경은 `847c63d`, `7700bd8`이다
- 일시: 2026-11-03T01:32:00+09:00

## 요약

r1 지적 7건 중 4건(1, 4, 5, 6)은 해결됐고, 1건(2)은 코드만 해결되고 회귀 테스트가 없으며, 2건(3, 7)은 일부만 해결됐다. 항목 3의 수정은 새로운 오판을 만들었다. r1이 놓친 지적 2건을 이번에 추가한다. Scenario 27개 중 충족 24개, 부분 충족 3개, 미충족 0개다. 전부 스펙을 고치지 않고 해결할 수 있다.

## r1 지적 대조

| # | r1 지적 | 결과 | 증거 |
| --- | --- | --- | --- |
| 1 | `content: null`과 빈 `choices`가 호출 상한을 넘긴다 | 해결 | `apps/worker/src/worker/llm.py:287-292`. 실측: 둘 다 2회 호출 후 `LlmSchemaError`, 비재시도 · 테스트 `apps/worker/tests/test_output_contract.py:369`, `apps/worker/tests/test_llm_gateway.py:270`. 같은 부류의 다른 입력은 조치 항목 2 |
| 2 | 앵커가 붙은 공백·placeholder 페이지 저장 | 코드 해결, 테스트 없음 | `apps/worker/src/worker/handlers/compile.py:68`. 실측: `[[src:s1]]`, `TODO [[src:s1]]`, `{{title}} [[src:s1]]`, `[[wi[[wiki:w8]]ki:w1]]`이 제목·본문 모두 `value_error`로 거부된다. 이를 단언하는 테스트는 없다 (조치 항목 5) |
| 3 | 근거 부족 표현의 부분 일치 | 일부 해결, 새 오판 | r1의 두 문장은 이제 위반이다. `없습니다`를 단독 대안으로 넣어 다른 일반 답변이 통과한다 (조치 항목 1) |
| 4 | 데이터가 없는데 품질 탭이 0을 표시 | 해결 | `apps/dashboard/components/ControlRoom.tsx:552` · 테스트 `apps/dashboard/tests/ControlRoom.test.tsx:530`, `:555` (`pages_total: 12`) |
| 5 | viewer 응답의 수집 필드 0 | 해결 | `apps/api/src/api/routers/control.py:559`, `:579`, `:589`, `ControlRoom.tsx:579` · 테스트 `apps/api/tests/test_control_router.py:912-913`, `apps/api/tests/test_tenant_isolation_full_path.py:667`, `ControlRoom.test.tsx`의 viewer 사례 |
| 6 | 로그 단언 테스트 없음 | 해결 | 테스트 `test_output_contract.py:416` (`worker.compile_fabricated_evidence` 개수 2), `:424` (`worker.conflict_pairs_unjudged` 개수 2) |
| 7 | task 5.2의 기본 모드 기록 누락 | 일부 해결 | `docs/ops/ask-sample-replay.md:19-21`에 기본값, 근거, 되돌리는 방법이 있다. `docs/reference/stack.md`에는 없고 `314a855` 표기의 설명이 사실과 다르다 (조치 항목 3) |

## 시나리오 판정

### grounded-answering

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| Ask 인용 계약과 수리 / 인용이 하나도 없는 답변을 수리한다 | 부분 충족 | 수리 경로는 충족한다 (`apps/api/src/api/services/ask.py:984-1007`, 테스트 `apps/api/tests/test_ask_router.py:1061`). `문서`, `자료`, `근거`가 든 일반 답변은 수리 없이 `resolved`로 저장된다 (조치 항목 1) |
| Ask 인용 계약과 수리 / 근거 부족을 밝힌 답변 | 충족 | `packages/core/src/nexuswiki_core/answer_contract.py:44-47`. 시드 문구 `0006:151,184`와 일치 · 테스트 `test_ask_router.py:1084`, `packages/core/tests/test_answer_contract.py:59` |
| Ask 인용 계약과 수리 / 정상 답변 | 충족 | `answer_contract.py` `check_answer_contract` · 테스트 `test_ask_router.py:1046`, `test_answer_contract.py:69` |
| 결정론적 Ask Fallback / 수리도 실패한다 | 충족 | `ask.py:1000-1013`, `answer_contract.py:85-87`, `:113` · 테스트 `test_ask_router.py:1095`, `test_answer_contract.py:94` |
| 결정론적 Ask Fallback / 수리 호출 자체가 실패한다 | 충족 | `ask.py:636-639` (모든 예외를 종결 경로로 보낸다) · 테스트 `test_ask_router.py:1095`, `:1134`, `:1143` |
| 결정론적 Ask Fallback / 근거 본문에 앵커 문법이 들어 있다 | 충족 | `answer_contract.py:87`, `packages/core/src/nexuswiki_core/citations.py:43-49` · 테스트 `test_answer_contract.py:80`, `:94` (중첩 앵커) |
| 결정론적 Ask Fallback / 기록을 다시 연다 | 충족 | 변경 없음. r1 증거 유지 (`apps/dashboard/components/AskConversation.tsx`, `0029`) · 테스트 `apps/dashboard/tests/AskThreadHistoryRestore.test.tsx:182`. 근거 목록 본문은 단언하지 않는다 |
| 품질 통제 모드 / shadow 모드의 위반 | 충족 | `ask.py:975-984` · 테스트 `test_ask_router.py:1119` |
| 품질 통제 모드 / off 모드 | 충족 | `ask.py:975` · 테스트 `test_ask_router.py:1127` |

### wiki-compilation

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| 코드 펜스와 의미 검증 / 펜스로 감싼 정상 JSON | 충족 | `llm.py:70`, `:113-122` · 테스트 `test_output_contract.py:111`, `apps/worker/tests/test_controlled_ai_evidence.py:294` |
| 코드 펜스와 의미 검증 / placeholder 페이지 | 충족 | `compile.py:59-71`, `:96` · 테스트 `test_output_contract.py:175`, `test_controlled_ai_evidence.py:302`. 앵커 결합 입력은 실측으로만 확인했다 (조치 항목 5) |
| 코드 펜스와 의미 검증 / 본문이 템플릿 문법을 설명한다 | 충족 | `compile.py:59-61` (전체 일치) · 테스트 `test_output_contract.py:187` |
| 호출 상한 / 어떤 입력에도 호출은 2회를 넘지 않는다 | 부분 충족 | 스키마 위반과 내용 없는 응답은 2회로 끝난다 (`llm.py:64`, `:287-292`, `apps/worker/src/worker/errors.py:173-180`, 테스트 `test_output_contract.py:125`, `:140`, `:369`). HTTP 200의 나머지 깨진 응답은 큐로 빠진다 (조치 항목 2) |
| 호출 상한 / 파싱할 수 없는 출력의 재시도 | 충족 | `llm.py:528-538` · 테스트 `test_output_contract.py:145`, `:156`, `:443` |
| 페이지 근거 청크 / 발급되지 않은 앵커 | 충족 | `compile.py:173`, `:287`, `:430-441` · 테스트 `test_output_contract.py:343`, `:416`, `:460` |
| 페이지 근거 청크 / 재컴파일 | 충족 | `supabase/migrations/0030_wiki_page_evidence.sql:68-80` · 테스트 `supabase/tests/wiki_page_evidence.sql` (RPC 2회 호출, 직접 실행 통과). 핸들러를 두 번 도는 테스트는 없다 |
| 페이지 근거 청크 / 다른 워크스페이스 사용자의 조회 | 충족 | `0030:43-48` · 테스트 `supabase/tests/wiki_page_evidence.sql:69-70` (직접 실행 통과) |
| 충돌 판정 쌍 격리 / 한 쌍만 스키마를 어긴다 | 충족 | `apps/worker/src/worker/handlers/conflict.py:133-135`, `:145` · 테스트 `test_output_contract.py:242`, `:424` |

### ai-control-room

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| 품질 탭 / editor가 품질 탭을 연다 | 부분 충족 | 집계와 화면은 있다 (`control.py:543-594`, `supabase/migrations/0031_control_quality_tab.sql`, `ControlRoom.tsx:549-614`, 테스트 `test_control_router.py:814`, `ControlRoom.test.tsx:452`). 시도 위반 코드 `missing_content`가 집계되지 않는다 (조치 항목 4) |
| 품질 탭 / viewer가 품질 탭을 연다 | 충족 | `control.py:579`, `:589`, `0031:74`, `:96`, `:108` · 테스트 `test_control_router.py:912-913`, `test_tenant_isolation_full_path.py:667` |
| 품질 탭 / 비멤버의 요청 | 충족 | `0031:47-50` · 테스트 `test_control_router.py:814`, `test_tenant_isolation_full_path.py:649` |
| 품질 탭 / 집계할 데이터가 없다 | 충족 | `ControlRoom.tsx:552` · 테스트 `ControlRoom.test.tsx:530` |

### ai-controls-showcase

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| 전후 증거 / 충돌 판정 비용 누락의 전후 비교 | 충족 | `apps/dashboard/components/ControlledAiShowcase.tsx` · 테스트 `test_controlled_ai_evidence.py:979`, `apps/dashboard/tests/ControlledAiShowcase.test.tsx:56` |
| 전후 증거 / Step 2 예산 및 단락 시나리오의 전후 비교 | 충족 | 같은 렌더 경로, `apps/dashboard/content/controlled-ai/step1.json` · 테스트 `test_controlled_ai_evidence.py:979` |
| 전후 증거 / Step 3 출력 계약 시나리오의 전후 비교 | 충족 | `test_controlled_ai_evidence.py:294`, `:302`, `:621`, `:848-875`. `7700bd8`은 10개 시나리오의 `after.commit`만 `847c63d`로 바꿨고 그 커밋은 HEAD의 조상이다. `before` 값은 그대로이며 r2에서 다시 측정하지는 않았다 |
| 전후 증거 / 증거 파일의 내용 검사 | 충족 | 테스트 `test_controlled_ai_evidence.py:1040` |
| 전후 증거 / 아직 구현되지 않은 단계 | 충족 | 테스트 `test_controlled_ai_evidence.py:1022`, `ControlledAiShowcase.test.tsx:99-111` |

## 조치가 필요한 항목

1. **`없습니다` 단독 대안이 인용 없는 일반 답변을 `resolved`로 저장한다** (r1 항목 3의 잔여이자 수정이 만든 회귀) — `answer_contract.py:45-46`은 `자료|컨텍스트|근거|문서` 뒤 30자 안에 `없습니다`가 있으면 근거 부족으로 본다. Ask 경로로 실측했다.
   - `문서 업로드 용량에는 제한이 없습니다.`: 호출 1회, `resolved`, 위반 `[]`. 수정 전 패턴에서는 위반이었다.
   - `문서를 찾을 수 없으면 관리자에게 문의합니다.`: 호출 1회, `resolved`, 위반 `[]`.
   - 순수 함수로 같은 결과를 확인한 문장: `자료 보관 기간에는 별도 제한이 없습니다.`, `근거 조항에 따르면 반품 수수료는 없습니다.`, `이 문서는 승인 절차가 필요 없습니다.`

   위키 제품이라 `문서`와 `자료`는 일반 답변에 흔한 단어다. 근거: "답변이 있는데 해소된 인용이 하나도 없으면 위반이다", design Goals "인용 없는 답변의 `resolved` 저장 차단". D5가 허용한 것은 표현을 놓쳐 수리가 1회 느는 방향뿐이다. 제안: 답할 수 없음을 밝히는 문형으로 좁힌다(`자료로는 ... 알 수 없`, `자료에서 ... 찾을 수 없습니다`, `자료에 해당 내용이 없습니다`처럼 조사와 대상까지 고정하고 `없습니다` 단독 대안은 뺀다). 위 문장들과 r1의 `파일을 찾을 수 없으면 ...`(현재 테스트에 없다)를 음성 사례로, `제공된 자료로는 답변할 수 없습니다.`를 양성 사례로 테스트에 넣는다.

2. **HTTP 200의 나머지 깨진 응답이 호출 상한 밖으로 빠진다** (신규, r1이 놓침) — 항목 1의 수정은 `_read_content`의 `ProviderError`만 잡는다. 실측:
   - 본문이 HTML이거나 JSON 객체가 아닌 응답(`llm.py:280`, `:442-453`): 1회 호출 후 `ProviderError(non_json_response)`, 재시도 대상.
   - `choices[0].message`가 문자열인 응답(`llm.py:475`): 1회 호출 후 `AttributeError`, 재시도 대상. 이 예외는 `except ProviderError`에 잡히지 않고 `on_attempt`(`:293`) 앞에서 나가므로 그 응답의 `usage`가 기록되지 않는다.

   큐의 `max_attempts` 기본값이 3(`supabase/migrations/0003_jobs.sql:48`)이므로 계속 이런 응답이면 잡 하나가 3회 호출한다. 실제 큐를 돌린 값이 아니라 계산한 값이다. 근거 Scenario: "어떤 입력에도 호출은 2회를 넘지 않는다 ... 두 호출의 비용이 모두 기록되며 잡은 재시도 없이 안전하게 종결된다". 5xx와 전송 실패는 r1과 같이 "잘못된 응답"으로 세지 않았다. 200 응답의 깨진 본문은 공급자가 돌려준 잘못된 응답으로 판단했다. 제안: `_read_content`가 `message` 형태를 확인해 `missing_content`로 분류하게 하고, 파싱 불가 본문과 객체가 아닌 본문도 `_read_body` 단계에서 같은 시도 위반으로 센다. 두 입력의 호출 수와 예외 종류를 단언하는 테스트를 추가한다.

3. **task 5.2가 완료인데 `docs/reference/stack.md`에 기본 모드 기록이 없다** (r1 항목 7의 잔여) — task는 "`docs/reference/stack.md`와 `docs/ops/`에 기록한다"이다. `AI_CONTROL_QUALITY_MODE`는 `docs/` 중 `docs/ops/ask-sample-replay.md:21`에만 있다. 또 같은 문서 `:36`의 "`314a855`는 squash 머지 전 작업 커밋이라 머지 뒤 `main` 이력에는 없다"는 사실과 다르다. `314a855`(`wip: 출력 계약 중간 저장`)는 amend로 교체된 커밋이라 지금도 이 브랜치의 조상이 아니고 어느 브랜치에도 포함되지 않으며 reflog에만 남아 있다. 게다가 이 커밋의 `_ABSTENTION`은 r1 이전 패턴이다. 따라서 기본값의 근거인 "위반 0/30"은 HEAD의 판정 로직으로 잰 값이 아니고, 문서는 그 사실을 적지 않았다. 제안: `stack.md`의 설정 절(`:81`)에 기본값과 되돌리는 방법을 적고, `:36`을 "브랜치 이력에 남지 않은 중간 커밋의 재생이며 이후 판정 패턴이 바뀌었고 다시 재생하지 않았다"로 고친다. 유료 재생을 다시 돌릴지는 사람이 정할 일이며 이 지적의 조건이 아니다.

4. **품질 탭이 `missing_content` 시도 위반을 세지 않는다** (신규, r1이 놓침) — `0031:91-93`은 `json_invalid`, `schema_invalid`, `semantic_invalid`만 센다. `missing_content`는 `usage_events.metadata.violation`에 남지만(`llm.py:290`, 테스트 `test_output_contract.py:369`) 집계 컬럼이 없다. 첫 시도가 내용 없이 오고 재시도가 성공한 호출은 어느 위반 칸에도 나타나지 않고, 소진되면 `시도 소진`만 오른다. 항목 1의 수정으로 이 코드가 정식 시도 위반이 되면서 공백이 뚜렷해졌다. 근거 Requirement: "구조화 출력의 시도 위반 ... 집계를 SHALL 제공한다". 제안: `0031`에 `structured_missing_content`를 추가하고 `control.py`, `ControlRoom.tsx`, 테스트에 칸을 연결한다. `docs/reference/stack.md`에 따르면 `0031`은 운영 미적용이지만 로컬 스택에는 적용돼 있어 반환 컬럼을 바꾸면 다시 적용해야 한다.

5. **앵커가 붙은 placeholder 거부에 회귀 테스트가 없다** (r1 항목 2의 잔여) — 코드는 실측으로 거부되지만 `test_output_contract.py:171-175`의 입력에 앵커 결합 값이 없고, `:363`은 정상 본문의 앵커 제거만 본다. r1이 요구한 테스트가 빠져 있어 `compile.py:68`을 되돌려도 어떤 테스트도 실패하지 않는다. 근거 Scenario: "그 응답은 검증 실패이고 잘못된 페이지는 저장되지 않는다". 제안: `[[src:s1]]`, `TODO [[src:s1]]`, `{{title}} [[src:s1]]`을 매개변수에 추가한다.

## 설계 결정 대조

| 결정 | 결과 | 비고 |
| --- | --- | --- |
| D1 기록 후 판정, 예외 없는 분류 | 부분 일치 | `llm.py:283-308`. `AttributeError` 경로가 기록 앞에서 나간다 (항목 2). 문장 "`_read_content`의 예외도 기록 뒤에 다시 던진다"(`design.md:22`)는 HEAD와 맞지 않는다 |
| D2 펜스 한 겹 | 일치 | `llm.py:70`, `:113-122` |
| D3 placeholder 전체 일치 | 일치 | 앵커 제거 뒤 판정으로 고쳐졌다 (`compile.py:68`) |
| D4 2회와 비재시도 | 부분 일치 | 내용 없는 응답까지 들어왔다. 깨진 본문이 남았다 (항목 2) |
| D5 두 코드 | 불일치 | 코드는 둘이다. 표현 판정이 "놓치는 방향"을 넘어 과대 일치한다 (항목 1) |
| D6 사후 수리와 2,000토큰 초안 | 일치 | `ask.py:599-640`, `:984-1007` |
| D7 `fallback` 상태와 본문 정리 | 일치 | 정리 함수가 `strip_forged_anchors`로 바뀌어 중첩도 지운다. 문장의 `BROAD_ANCHOR_PATTERN` 표기만 옛 이름이다 |
| D8 근거 테이블과 범위 교체 | 일치 | `0030:19-34`, `:54-85` |
| D9 품질 집계 형태와 타입 확인 | 일치 | `0031:56-67`. 코드 누락은 항목 4 |

## 수정으로 깨진 시나리오 확인

- 항목 3의 수정이 `인용이 하나도 없는 답변을 수리한다`를 새 입력에서 깨뜨렸다 (조치 항목 1). 그 밖에 깨진 Scenario는 찾지 못했다.
- `compile.py:173`의 발급 판정을 전체 조각 포함으로 바꾼 것은 안전하다. `_join_within_budget`(`compile.py:351-366`)은 조각을 중간에서 자르지 않고 `[[src:s1]]`과 `[[src:s10]]`은 닫는 괄호로 구별된다.
- 토크나이저 호출 2곳(`chunking.py:90`, `context_budget.py:126`)이 모두 `disallowed_special=()`을 쓴다. 다른 호출 지점은 없다.

## 검증 실행

- `uv run pytest` (worker 6개, api 3개, core 3개 파일): 301 passed. r1의 `wiki_links` 준비 단계 오류는 재현되지 않았다. 원인은 여전히 모른다.
- `uv run pytest packages/core/tests`: 189 passed. `apps/api/tests/test_ask_citations.py`: 3 passed.
- `pnpm exec vitest run` (`ControlRoom`, `ControlledAiShowcase`, `AskThreadHistoryRestore`): 27 passed. `AskConversation`: 12 passed. `tsc --noEmit`: 오류 없음.
- `uv run ruff check` (api, worker, core의 `src`): 통과. `openspec validate ai-control-output-contract --strict`: valid.
- `supabase/tests/wiki_page_evidence.sql`을 `docker exec psql`로 실행: 오류 없이 ROLLBACK까지 진행. `supabase test db`는 실행하지 않았다.
- 로컬 스택은 0034까지 적용돼 있고 0032~0034는 다른 브랜치 것이다. 0031만 적용된 깨끗한 스택에서의 결과는 확인하지 못했다.
- 위 "실측"은 HEAD 코드에 합성 입력을 넣어 재현한 것이며 임시 스크립트는 저장소 밖에 두었다. 실제 LLM 재생은 돌리지 않았다.

## 참고 (판정에 넣지 않음)

- 제목의 앵커는 검증에서만 지우고 저장할 때는 그대로다(`compile.py:410`). 실측: 제목 `정상 본문 [[src:s1]]`이 통과한다. r1은 정리를 제안했지만 스펙에는 요구가 없다. Fallback은 표시할 때 지운다(`answer_contract.py:113`). 다른 표시 경로는 확인하지 않았다.
- HTTP 200의 `{"error": ...}` 본문은 이제 2회 호출 후 `LlmSchemaError`로 끝난다. 수정 전에는 큐가 재시도했다. 호출 상한에는 맞지만, 일시 장애가 이 형태로 오면 컴파일 잡은 바로 `dead`가 되고 충돌 판정 쌍은 미판정으로 넘어간다. 공급자가 실제로 이 형태를 얼마나 보내는지는 확인하지 못했다.
- 수리 호출 비용은 r1과 같이 코드 경로로만 확인했고 경계까지 통과시키는 테스트는 없다.
- `repair` 구간이 추적 라벨에 추가됐다(`control.py`의 `_SPAN_LABELS`, `observability.py`의 `_SPAN_NAMES`). r1 참고 사항의 반영이고 이를 단언하는 테스트는 없다.

## 판정 근거

r1의 미충족 2건은 해소됐지만, 항목 3 수정이 인용 없는 답변의 `resolved` 저장 경로를 다른 입력으로 남겼고, 호출 상한과 품질 집계에 부분 충족이 있으며, task 5.2의 기록과 회귀 테스트도 빠져 있어 `pass`가 아니다. 어느 것도 스펙 변경이나 사람의 결정을 요구하지 않고 스펙 범위 안에서 코드·테스트·문서를 고치면 해결되므로 `needs_fix`다. 리뷰 게이트의 상한상 다음 라운드가 마지막이다.

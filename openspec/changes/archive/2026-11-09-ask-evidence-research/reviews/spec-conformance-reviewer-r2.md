# Spec Conformance 리뷰 — ask-evidence-research r2

- 판정: pass
- 대상: 기준 HEAD `5dded7b220147489e071d6e7f9d562af07834e11` 위의 미커밋 작업 트리 (`/private/tmp/nexuswiki-evidence-research`, `git diff` + 신규 파일)
- 일시: 2026-11-09T00:36:10Z
- 이전 라운드: `spec-conformance-reviewer-r1.md` (needs_fix, 조치 4건)
- 이번 리뷰에서 새로 실행한 검증
  - `uv run --offline pytest -q apps/api/tests/test_ask_router.py apps/api/tests/test_evidence_research.py apps/worker/tests/test_evidence_research_eval.py packages/core/tests/test_evidence_research.py` → 90 passed
  - `vitest run tests/EvidenceResearchShowcase.test.tsx` → 5 passed
  - `tsc --noEmit` 오류 없음, 변경된 대시보드 두 파일 `eslint` 문제 없음
  - `openspec validate ask-evidence-research --strict` → valid
  - 현재 작업 트리의 `execution_sha256()` = `dfda4a4d…2d08`. 공개 기록 `conditions.execution`과 같다

## r1 조치 항목 대조

| # | r1 지적 | 결과 | 증거 |
| --- | --- | --- | --- |
| 1 | 공개 페이지가 반복 횟수와 회귀 분모를 틀리게 표시("3회 합계", `/ 90`, "42문항씩 3회", 1~3차 선택지) | 해소 | 쌍 수·분모를 기록에서 계산 `apps/dashboard/components/EvidenceResearchShowcase.tsx:100-110`(`pairs` = 행의 고유 pair, `regressionTotal` = `type==="regression"` 행 수, `perPair`). 요약 행 라벨과 분모 `:134-140`(1쌍이면 "기존 문항 통과", 분모 30). 캡션 `:228-232` → "OFF / ON · 42문항 1쌍, 전체 호출 포함". 실행 쌍 선택지 `:279-283`은 `pairs`만 렌더한다(현재 1개). 확인: 공개 JSON은 `rows` 42개 전부 pair 1, regression 30개. `type==="regression"` ⇔ `id`가 `q`로 시작해서, export의 `regression_passed`(`scripts/evidence_research_eval.py:208-210`) 집계 기준과 분모 기준이 같다. OFF/ON 각각 28/30으로 표시된다. 공지(`:192-196`) "OFF/ON 한 쌍"과도 이제 모순되지 않는다 |
| 2 | 유효 결과 렌더링 테스트 없음 | 해소 | `apps/dashboard/tests/EvidenceResearchShowcase.test.tsx:80-112`가 실제 `content/evidence-research.json`(valid=true)을 렌더한다. 검증 항목: 불채택 제목, 캡션 "42문항 1쌍", 기존 문항 행의 OFF/ON 칸 `28 / 30`, 표에 "3회" 없음, "복구율은 미측정", 실행 쌍 선택지 1개, 상태 "42문항". r1의 결함 문구("3회"·`/ 90`·선택지 3개)를 되살리면 각각 단언이 깨진다. 추가 테스트 `:114-140`는 무효 기록에서 "· 복구"가 없는지 확인한다 |
| 3 | 평가 재개 거부 경로 미검증 | 해소 | manifest 지문 없음·불일치 `apps/worker/tests/test_evidence_research_eval.py:74-83`: `httpx.Client`·`_ask_once`를 호출 즉시 실패하는 대역으로 바꾸고, `SystemExit("…실행 코드 지문…")`와 출력 파일 미생성을 확인한다(대상 `scripts/evidence_research_eval.py:80-82`). 재개 원본 불일치 `:86-135`: 같은 조건이면 거부 단계를 통과해 첫 유료 호출 대역에 도달한다는 대조군이 있다(`:118-122`). 실행 지문만 다른 경우(`:124-130`)와 모드만 다른 경우(`:132-135`)는 `SystemExit("재개 원본의 비교 조건…")`로 거부된다(대상 `:102-109`). 대조군 덕분에 이 거부가 조건 비교에서 나온 것임이 확인된다 |
| 4 | 권한·예산 거부가 오류 턴으로 끝나는지 미검증 | 해소 | `apps/api/tests/test_ask_router.py:319-373`, 세 경우를 매개변수로 돈다. ① 판단 호출 402 → `budget_exceeded` ② 판단 호출 403 → `forbidden` ③ 판단은 정상 tool_call, 재검색 직전 `has_workspace_role`=false → `forbidden`. 세 경우 모두 SSE `meta,citations,done`, `citations.error`=기대 토큰, `finalize_ask_turn.p_status="error"`, 모델 호출 1회(판단만)를 확인한다. 답변 호출이 생기면 `:341`의 assert가 실패한다. 대상 경로: `apps/api/src/api/services/ask.py:726-731`(402/403 → `ResearchDenied`), `:753-761`(멤버십 회수), `:772-773`(재전파), `:1133-1138`(`exc.token`으로 오류 턴 종료). `has_workspace_role`을 쓰는 곳은 Ask 경로에서 `ask.py:754` 한 곳뿐이다. 그래서 ①②에서 false 응답은 쓰이지 않고, ③만 멤버십 경로를 탄다 |

r1 권고 중 "무효 상태의 행별 '· 복구' 숨김"도 반영됐다: `EvidenceResearchShowcase.tsx:319`(`data.valid && row.answer_recovered`), 테스트 `:114-140`.

## 수정이 새 문제를 만들었는지

- r1 이후 바뀐 파일: `EvidenceResearchShowcase.tsx`, `EvidenceResearchShowcase.test.tsx`, `test_ask_router.py`, `test_evidence_research_eval.py`, `apps/api/src/api/services/ask.py`(mtime 기준)
- `ask.py`는 수정 시각만 바뀌었다. API·워커·core 소스 전체의 내용 지문 `execution_sha256()`이 측정 기록의 `dfda4a4d…2d08`과 여전히 같다. 따라서 실행 코드 내용은 측정 당시와 같고, 공개 결과는 리뷰한 코드로 만든 것이다
- `content/evidence-research.json`은 r1 이후 바뀌지 않았다(r1에서 export 재생성 결과와 같음을 확인)
- 무효 상태(`valid=false`) 동작은 그대로다. 표와 복구 수치는 숨겨지고 조건·장애 점검 항목만 남는다(`:208-214`, `:253-259`). 기존 테스트 `:29-40`도 통과한다
- controlled-ai 연결 유지: `apps/dashboard/components/ControlledAiShowcase.tsx:87`
- 새로 생긴 미충족 Scenario는 없다

## 시나리오 판정

r1에서 충족으로 본 Scenario는 해당 코드 내용이 바뀌지 않았으므로(실행 지문 동일) r1 증거를 그대로 쓴다. 줄 번호는 현재 파일에서 다시 확인했다.

### ask-evidence-research

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| Bounded model-selected evidence research / Missing comparison target | 충족 | `ask.py:697-771`, `:1084-1111` · 테스트 `test_ask_router.py:209-316`, `apps/api/tests/test_evidence_research.py:112-120` |
| 〃 / Sufficient evidence or disabled mode | 충족 | `ask.py:771`, `:1084`, `settings.py:75` · 테스트 `test_evidence_research.py:157-161` |
| 〃 / No initial evidence | 충족 | `ask.py:1030-1061` · 테스트 `test_ask_router.py:175-205` |
| Server-owned research authorization and validation / Invalid tool batch | 충족 | `packages/core/src/nexuswiki_core/evidence_research.py:28-48,70-97`, `ask.py:788-798` · 테스트 `packages/core/tests/test_evidence_research.py:15-29` |
| 〃 / Cross-tenant request | 충족 | `evidence_research.py:41-42`, `ask.py:753-768` · 테스트 `test_evidence_research.py:112-115,152-154`, `test_ask_router.py:319-373`(회수 경우) |
| Evidence budget and stream continuity / Duplicate evidence and oversized context | 충족 | `evidence_research.py:51-59`, `ask.py:1099-1112` · 테스트 `packages/core/tests/test_evidence_research.py:66-69`. 재검색 경로의 예산 초과 절단 직접 테스트는 여전히 없다(권고, r1과 같음) |
| Research failure and cost visibility / Timeout or malformed decision | 충족 | `ask.py:734-748,786-798` · 테스트 `test_evidence_research.py:132-149,170-173` |
| 〃 / Authorization or budget denied | 충족 | `ask.py:726-731,753-761,772-784,1133-1138` · 테스트 `test_ask_router.py:319-373`(r1 #4 해소), `test_evidence_research.py:152-154,164-167`, `test_retrieval_service.py:44-60` |
| 〃 / Decision call consumed tokens without searching | 충족 | `apps/worker/src/worker/llm_stream.py:136-143,196-222`, `scripts/ask_replay.py:899-944` · 테스트 `test_evidence_research.py:132-140` |

### ask-replay-scorecard

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| Paired evidence research evaluation / Matched pair | 충족 | `scripts/evidence_research_eval.py:83-100,160-166,200-219` · 테스트 `test_evidence_research_eval.py:186-` |
| 〃 / Corpus or policy changed | 충족 | `evidence_research_eval.py:148-152`, export 차단 `:236-248` · 테스트 `test_evidence_research_eval.py:186-` |
| 〃 / Decision implementation changed during resume | 충족 | `evidence_research_eval.py:80-82,102-109` · 테스트 `test_evidence_research_eval.py:74-83,86-135`(r1 #3 해소) |
| Recovery scoring uses missing initial evidence / Missing target recovered | 충족 | `evidence_research_eval.py` 복구 분모·근거/답변 분리 · 테스트 `test_evidence_research_eval.py:186-` |
| 〃 / No eligible initial failures | 충족 | `rate=None` · 테스트 `test_evidence_research_eval.py:22-26`. 공개 사본 `recovery.rate=null`, 화면 "복구율은 미측정입니다" `EvidenceResearchShowcase.tsx:222-223` · 테스트 `EvidenceResearchShowcase.test.tsx:106` |

### retrieval-evaluation-showcase

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| Public evidence research comparison page / Published matched evaluation | 충족 | 조건 일치 점검 `EvidenceResearchShowcase.tsx:253-267`, OFF/ON 요약 `:126-168,226-250`(분모·쌍 수를 기록에서 계산 `:100-110`), 문항별 전후 결과와 필터 `:270-364`, 방법·한계·조건 해시 `:366-395`, JSON 다운로드 `:396-402`. 표본·반복 횟수 표시: 공지 `:192-196`, 캡션 `:228-232` · 테스트 `EvidenceResearchShowcase.test.tsx:80-112`(r1 #1·#2 해소) |
| 〃 / No valid result | 충족 | `:199-214,253-259,319` · 테스트 `EvidenceResearchShowcase.test.tsx:29-40,114-140` |
| Static allowlisted synthetic evaluation data / Offline result rendering | 충족 | `app/showcase/evidence-research/page.tsx`, `results.json/route.ts`(정적 import, `force-static`) · 테스트 `EvidenceResearchShowcase.test.tsx:142-154`, `test_evidence_research_eval.py:138-` |
| 〃 / Untrusted result text | 충족 | React 텍스트 노드만 사용 · 테스트 `EvidenceResearchShowcase.test.tsx:42-78` |

## 조치가 필요한 항목

없음.

권고(판정에 영향 없음):

1. 공지 `EvidenceResearchShowcase.tsx:193-195`("42문항", "OFF/ON 한 쌍")와 필터 라벨 `:293`("재검색 전용 12문항")은 아직 고정 문자열이다. 지금은 export가 `EVALUATION_PAIRS=(1,)`와 정확히 2개 기록일 때만 `valid=true`를 내고(`evidence_research_eval.py:22,237-241`) fixture가 30+6+6으로 고정돼 있어 데이터와 어긋나지 않는다. 다만 쌍 수나 fixture가 바뀌면 r1과 같은 종류의 불일치가 다시 생길 수 있다. 같은 계산값(`pairs`, `perPair`)을 쓰면 좋다.
2. 유효 렌더링 테스트(`EvidenceResearchShowcase.test.tsx:80-112`)는 기대값을 컴포넌트와 같은 방식으로 데이터에서 계산한다. 현재는 공개 JSON이 고정이고 "3회" 부재와 `valid=true`를 따로 단언해서 충분하다. 다만 `28 / 30`, `42문항 1쌍` 같은 리터럴 단언을 하나 두면 계산식 자체의 오류도 잡힌다.
3. r1 권고 중 남은 것: 재검색 경로에서 예산 초과 본문이 잘리는지, 워커 판단 출력 상한 `min(…, 256)`과 정산이 맞는지 직접 보는 테스트.

## 판정 근거

r1의 조치 4건이 모두 해소됐다. 공개 페이지는 쌍 수와 회귀 분모를 기록에서 계산해 실제 1쌍·28/30을 표시하고, 공지와도 모순되지 않는다. 실제 공개 기록으로 유효 상태를 렌더하는 테스트가 그 값을 단언한다. 평가 재개 거부(지문 없음·불일치, 원본 조건·모드 불일치)와 권한·예산 거부의 오류 턴 종료(402/403/멤버십 회수 → `citations.error`, `p_status=error`, 답변 호출 없음)는 이제 테스트가 있다. 재개 거부 테스트에는 같은 조건이면 통과한다는 대조군도 있다. 수정 후에도 실행 코드 지문은 측정 기록과 같아서, 공개 결과와 리뷰한 코드가 일치한다. 새로 생긴 미충족 Scenario는 없다. 남은 것은 판정에 영향 없는 권고뿐이므로 `pass`다.

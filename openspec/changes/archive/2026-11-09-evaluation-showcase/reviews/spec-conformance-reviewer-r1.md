# Spec Conformance 리뷰 — evaluation-showcase r1

- 판정: needs_fix
- 대상: 작업 트리(미커밋) 기준 `main...HEAD` + 작업 트리 변경 (HEAD `0f9bbbe72f65de47e304f8cd1898fc1853a94274`)
- 일시: 2026-11-09T13:20:00+09:00

## 검증 실행 (이번 라운드에 새로 실행)

| 명령 | 결과 |
| --- | --- |
| `uv run pytest apps/worker/tests/test_evaluation_showcase.py -q` | 50 passed |
| `uv run python scripts/evaluation_showcase.py check apps/dashboard/content/evaluation.json` | 검사 통과 |
| `pnpm --dir apps/dashboard exec vitest run tests/EvaluationShowcase.test.tsx` | 19 passed |
| 보존 report로 재export 후 커밋 대상 JSON과 비교(`generated_at` 제외) | 동일 |
| `reliability-report.json` sha256 | `636ffcc6…2c35` — `apps/dashboard/content/evaluation.json`의 `provenance.report_sha256` · `archive/2026-11-09-eval-reliability/verification.md:83`과 일치 |
| curated · fixture · labels 파일 sha256 | `provenance`의 세 값과 일치. curated `map`/`ledger` == 공개 기록 `map`/`ledger` |

typecheck · lint · 375px 확인은 이 리뷰 범위 밖이라 다시 실행하지 않았다(호출자 보고만 있음).

## 시나리오 판정

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| Public evaluation overview page / Anonymous visitor opens the page | 충족 | 다섯 구역 `apps/dashboard/components/EvaluationShowcase.tsx:423,541,595,640,688` · 결론 `:401-405`, `:135-155` · 합성 샘플 notice `:407-414` · 미들웨어 matcher가 `/showcase/*`를 포함하지 않음 `apps/dashboard/middleware.ts:81` · 정적 페이지 `apps/dashboard/app/showcase/evaluation/page.tsx:10` · 테스트 `apps/dashboard/tests/EvaluationShowcase.test.tsx:28-40,267-275`. 비로그인 리다이렉트 없음은 자동 테스트가 없고 matcher 구조와 호출자의 로컬 확인에 의존한다 |
| Public evaluation overview page / Navigating between showcases | 충족 | 새 페이지 → 두 쇼케이스 `EvaluationShowcase.tsx:389-396,780-785` · `ControlledAiShowcase.tsx:92` · `EvidenceResearchShowcase.tsx:180` · 테스트 `EvaluationShowcase.test.tsx:313-339` |
| Evaluation map shows every measurement surface / Measured surface | 충족 | 비파생 칸: 상태 `EvaluationShowcase.tsx:622` · 수치·분모 `:213-225` · 측정일 `:629` · 출처 `:229-237`. 파생 칸은 `n/분모`를 series에서 조립 `:173-193`. `check`가 measured/partial 칸의 summary·denominator·measured_at·source 누락을 거부 `scripts/evaluation_showcase.py:544-548` · 테스트 `EvaluationShowcase.test.tsx:186-215`, `apps/worker/tests/test_evaluation_showcase.py:458-480` |
| Evaluation map shows every measurement surface / Empty surface | 충족 | 렌더 `EvaluationShowcase.tsx:212` · `check`가 empty 칸의 reason 필수, summary/denominator 금지 `evaluation_showcase.py:538-543` · 테스트 `EvaluationShowcase.test.tsx:217-234`, `test_evaluation_showcase.py:467-468` |
| Repetition grid / Known failure across all runs | 충족 | 예외 표 `EvaluationShowcase.tsx:510-536` · 칸 글자 상태 `:243-253` · 안정성 `:325` · 보고/자동 단계 설명 줄 `:327-339`, 문구 사전 `:110-121` · 데이터 `content/evaluation.json` q06 `outcomes=[fail×3]`, `reported_stage=question_ambiguity`, `automatic_stage=retrieval_miss` · 테스트 `EvaluationShowcase.test.tsx:120-139`, `test_evaluation_showcase.py:368-378` |
| Repetition grid / Mixed execution paths | 충족 | 회차 열 머리에 경로가 드러나는 공개 이름 `EvaluationShowcase.tsx:373-376,447-451` · 전체/HTTP만 최소·최대 `:486-505` · 합친 구간 없음 안내 `:506-509` · `check`의 http_only 재계산 `evaluation_showcase.py:476-484` · 테스트 `EvaluationShowcase.test.tsx:42-62`, `test_evaluation_showcase.py:219-230,261-267` |
| Repetition grid / Partially executed run | 충족 | 미실행 기호·글자 `EvaluationShowcase.tsx:243-253` · 미실행 칸이 있으면 펼침 `:240-241` · `check`가 회차 asked/passed를 칸에서 재집계하고 not_run을 제외 `evaluation_showcase.py:633-650`, 안정성 재유도 `:587` · 테스트 `EvaluationShowcase.test.tsx:156-174`, `test_evaluation_showcase.py:392-404` |
| Refusal figures shown apart from pass rate / One unanswerable question | 부분 충족 | 정확한 거절 1/1 + "거절 문항 1개" `EvaluationShowcase.tsx:166-169,574-579` · 잘못된 거절 0/29 `:580-587` · "없음" 처리 `:167`, export `evaluation_showcase.py:194`, check `:405-408` · 테스트 `EvaluationShowcase.test.tsx:64-87`, `test_evaluation_showcase.py:233-243`. **단, 거절 성능 구역(`#refusal`, `:541-593`)에 회차별 "답할 수 있는 문항 통과 28/29"가 없다.** 28/29는 반복 측정 구역 요약표(`:463-470`)에만 있다 — 조치 1 |
| Application ledger in date order / Ledger entry rendered | 충족 | `<ol>` 렌더, 첫 문장 `changed` 후 기법·한 일·증거 `EvaluationShowcase.tsx:650-685` · `check` 날짜 오름차순·빈 changed 거부 `evaluation_showcase.py:551-571` · 테스트 `EvaluationShowcase.test.tsx:236-255`, `test_evaluation_showcase.py:471-472` |
| Reproduction conditions and limits / Limits visible with results | 충족 | 회차 수·독립 표본 아님 `EvaluationShowcase.tsx:697-700` · 흔들림 0의 의미 `:701-707` · 거절 표본 수 `:708-711` · 합성 샘플 한계 `limitations[0]` + notice `:407-414` · 모델·정책·k·비용 `:718-740` · 고정 입력 지문 3종 `:741-765` · 테스트 `EvaluationShowcase.test.tsx:277-293` |
| Static allowlisted record / Offline rendering | 충족 | JSON 정적 import + `force-static` `page.tsx:7,10`, `results.json/route.ts:1,3` · import 경계 테스트 `EvaluationShowcase.test.tsx:341-354` |
| Static allowlisted record / Untrusted record text | 충족 | 모든 문자열 텍스트 노드 렌더, `dangerouslySetInnerHTML` 없음(경계 테스트 `:352`) · `source_url`/`evidence_url`은 https만 허용 `evaluation_showcase.py:500-501` · 테스트 질문 `EvaluationShowcase.test.tsx:176-184`, 원장 `:257-265`, 한계 `:295-303` |
| Static allowlisted record / Forbidden field in record | 충족 | 전 계층 허용 목록 `evaluation_showcase.py:62-131,331-341` · 금지 이름 패턴 `:135-138,344-352` · export는 check 실패 시 쓰지 않음 `:684-689` · 커밋 파일을 CI pytest가 검사 `test_evaluation_showcase.py:490-492` · 테스트 `:270-283,311-336,483-487` |
| Static allowlisted record / Download matches the page | 충족 | 같은 `@/content/evaluation.json`을 그대로 반환 `results.json/route.ts:1,6-12` · 다운로드 링크 `EvaluationShowcase.tsx:777-779` · 테스트 `EvaluationShowcase.test.tsx:305-311` |
| Invalid or missing measurements / Series marked invalid | 충족 | 반복 측정·거절 구역 무효 `EvaluationShowcase.tsx:429-431,547-549,345-352` · export 무효 판정 `evaluation_showcase.py:231-242,257-263,270-279` · check가 무효 묶음의 수치 잔존 거부 `:460-465` · 테스트 `EvaluationShowcase.test.tsx:89-118`, `test_evaluation_showcase.py:286-308,442-448` |
| Invalid or missing measurements / Map and conclusion follow an invalid series | 충족 | 결론 `EvaluationShowcase.tsx:402-404` · 파생 지도 칸 `:196-202` · curated 파생 칸의 직접 값 금지 `evaluation_showcase.py:530-537` · 테스트 `EvaluationShowcase.test.tsx:107-117`, `test_evaluation_showcase.py:461-462` |

### tasks.md 1~3절 인수 조건 대조

| task | 결과 | 비고 |
| --- | --- | --- |
| 1.1 · 1.2 | 충족(1건 제외) | AC 9개 모두 대응 코드·테스트 있음. 비로그인 리다이렉트 없음은 자동 테스트 대신 matcher 구조로 성립. 거절 블록 AC는 tasks/D6가 스펙보다 좁게 적었다(조치 1) |
| 2.1 · 2.2 | 충족 | 문항 필드·불변식 `evaluation_showcase.py:214-228,574-651` · 격자·접기·q30 표시·scope 테스트 `EvaluationShowcase.test.tsx:120-174` |
| 3.1 | 부분 충족 | 10칸·7행 이관, 파생 칸 `derived_from`, 검색 행 2026-11-09 값, 도구 궤적 `empty`+이유, hit@8 0.589 제외는 확인. **"0.578 · 0.374는 옮기지 않는다"를 어기고 두 수치가 공개 화면에 실린다** — 조치 2 |
| 3.2 | 충족 | 지도·원장 렌더, `evaluation-map.md` §2 · §5를 curated 파일·페이지 링크로 대체(diff 확인) |

## 조치가 필요한 항목

1. **거절 성능 구역에 회차별 답할 수 있는 문항 통과가 없다** — 스펙은 거절 성능 구역이 "회차마다 답할 수 있는 문항 통과 · 정확한 거절 · 잘못된 거절을 각각 분모와 함께" 보이라고 요구하지만, `#refusal` 표(`EvaluationShowcase.tsx:561-589`)에는 정확한 거절과 잘못된 거절 두 행만 있다. 28/29는 반복 측정 구역 요약표에만 있어, 점프 목차의 "거절 성능"으로 바로 들어간 방문자는 같은 회차의 통과 수를 그 구역에서 볼 수 없다. 설계 D6 §3과 tasks 1.2 AC가 이 항목을 빼고 적어 조용히 범위가 줄었다. 근거 Scenario: "THEN 그 회차는 28/29 · 정확한 거절 1/1 · 잘못된 거절 0/29를 보이고 거절 표본이 1개임을 보인다". 제안: 거절 표 맨 위에 "답할 수 있는 문항 통과" 행(`answerable_passed/answerable_asked`)을 더하고, 테스트 `EvaluationShowcase.test.tsx:64-72`에 거절 표 안의 `28/29` ×3 단언을 더한다. 화면에 거절 수치와 통과율을 섞지 않는다는 스펙 제목의 취지는 행을 따로 두면 유지된다.

2. **출처에서 확인되지 않는 근거성 수치(0.578 · 0.374)가 공개 화면에 실린다** — `scripts/fixtures/evaluation_showcase.curated.v1.json:10`의 근거성 칸 `detail`이 "이전 지도에 적혀 있던 문장 비율 평균(0.578 · 0.374)은 … 옮기지 않았다"고 쓰면서 두 숫자를 그대로 적는다. 이 문장은 `EvaluationShowcase.tsx:219-224`의 "자세히"로 페이지에 나오고, JSON 다운로드에도 들어간다. tasks 3.1은 "옮기지 않는다", 설계 D4는 "출처에 없는 숫자를 공개 화면에 올리지 않기 위해서다"라고 적었다. 숫자를 "확인되지 않음"이라는 꼬리표와 함께 공개해도 숫자가 공개되는 건 같다. 근거: tasks 3.1 · 설계 D4 마지막 항목. 제안: `detail`에서 두 숫자를 빼고 "이전 지도의 문장 비율 평균은 출처 문서에서 확인되지 않아 옮기지 않았다" 정도로 남긴 뒤 다시 export한다(`curated_sha256`이 바뀐다).

## 참고 (판정에 영향 없음)

- 묶음이 무효일 때도 원장 2026-11-09 항목("세 회차 모두 28/29")과 지도 "비용 · 지연" 상세("회차 비용 약 $0.76")에는 반복 측정 수치가 남는다. 스펙의 무효 시나리오는 결론 · 반복 측정 구역 · 지도의 정답성/거절 칸만 대상으로 하고 원장은 과거 적용 기록이라 위반으로 보지 않았다. 무효 기록을 실제로 공개하게 되면 사람이 판단할 일이다.
- 설계 D6는 요약표에 "경로" 행을 두라고 했지만 구현은 경로를 열 머리의 공개 회차 이름("HTTP 1" · "스크립트 재집계 #232")으로 보인다. 스펙은 "회차마다 실행 경로 표시"만 요구하므로 충족이다.
- `ControlledAiShowcase`의 새 링크는 nav가 아니라 본문 `<p>`에 있다(`:91-95`). 스펙은 링크가 있으라고만 요구한다.
- 결론 문장은 D5 예문("매번 같은 이유로 틀렸습니다")이 아니라 "매번 같은 문항이었습니다"(`:152`)다. tasks AC가 요구하는 앞부분은 같다.
- 스펙 밖에서 사용자가 볼 수 있는 동작이 새로 생긴 곳은 찾지 못했다.

## 판정 근거

시나리오 16개 가운데 15개는 코드 경로와 테스트로 충족을 확인했다. 거절 성능 구역은 스펙이 명시한 세 수치 중 하나(답할 수 있는 문항 통과)를 그 구역에 보이지 않아 부분 충족이다. 별도로 tasks 3.1 인수 조건을 어기고 출처 미확인 수치가 공개 기록에 들어갔다. 둘 다 컴포넌트 표 한 행 추가와 curated 문장 수정·재export로 스펙을 바꾸지 않고 해결되므로 `needs_fix`다. 1번을 고치지 않고 "페이지 전체에 보이면 충분하다"로 정리하려면 스펙 문장을 고쳐야 하며, 그 경우는 `blocked`(사람 결정) 사안이 된다.

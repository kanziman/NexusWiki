# Spec Conformance 리뷰 — evaluation-showcase r2

- 판정: pass
- 대상: 작업 트리(미커밋) 기준 `main...HEAD` + 작업 트리 변경 (HEAD `0f9bbbe72f65de47e304f8cd1898fc1853a94274`)
- 일시: 2026-11-09T04:19:51Z

## 검증 실행 (이번 라운드에 새로 실행)

| 명령 | 결과 |
| --- | --- |
| `uv run pytest apps/worker/tests/test_evaluation_showcase.py -q` | 50 passed |
| `pnpm --dir apps/dashboard exec vitest run tests/EvaluationShowcase.test.tsx` | 19 passed |
| `uv run python scripts/evaluation_showcase.py check apps/dashboard/content/evaluation.json` | 검사 통과 |
| 보존 report(`636ffcc6…2c35`, 출처 일치)로 재export 후 커밋 대상 JSON과 비교(`generated_at` 제외) | 동일 |
| `shasum -a 256 scripts/fixtures/evaluation_showcase.curated.v1.json` | `40faab8f…8bac` — `evaluation.json`의 `provenance.curated_sha256`(`:8`)과 일치 |
| `grep -rn "0\.578\|0\.374"` (curated · content JSON · 컴포넌트 · 페이지 · `docs/ops/evaluation-map.md`) | 0건 |
| `openspec validate evaluation-showcase --strict` | valid |

대시보드 전체 테스트 · typecheck · lint · 375px 확인은 다시 실행하지 않았다(호출자 보고만 있음). 스펙 판정에는 해당 테스트 파일 단독 실행으로 충분하다.

## r1 지적 반영 확인

| r1 항목 | 결과 | 증거 |
| --- | --- | --- |
| 1. 거절 성능 구역에 회차별 답할 수 있는 문항 통과가 없음 | 해소 | `#refusal` 표 첫 행 "답할 수 있는 문항 통과" `apps/dashboard/components/EvaluationShowcase.tsx:574-581`(`answerable_passed/answerable_asked`), 정확한 거절 `:582-587`, 잘못된 거절 `:588-595`. 세 행 모두 `valid` 분기 안(`:547-549`)이라 무효일 때 수치가 나오지 않는다. 테스트 `apps/dashboard/tests/EvaluationShowcase.test.tsx:64-74`가 거절 표 안에서 `28/29`×3 · `1/1 (거절 문항 1개)`×3 · `0/29`×3을 단언. 설계 `design.md:116`(D6 §3)과 tasks 1.2 AC(`tasks.md:13`)도 세 수치로 고쳐져 스펙과 일치 |
| 2. 출처 미확인 근거성 수치(0.578 · 0.374)가 공개 기록에 실림 | 해소 | curated `scripts/fixtures/evaluation_showcase.curated.v1.json:10`과 export `apps/dashboard/content/evaluation.json:572`의 `detail`이 "이전 지도에 적혀 있던 문장 비율 평균은 출처 문서에서 확인되지 않아 옮기지 않았다."로 바뀌고 숫자 없음. 재export 결과가 커밋 파일과 동일하고 `curated_sha256`이 실제 파일 해시와 일치 |

## 시나리오 판정

r1 이후 코드 변경은 거절 표 한 행 추가(`EvaluationShowcase.tsx`에 8줄, `:574-581`)와 curated 문장 한 줄뿐이다. 따라서 `:581` 이후 r1 증거 줄 번호는 +8 이동했다(지도 `:603`, 원장 `:648`, 재현 조건 `:696`). 다른 시나리오의 코드 경로는 바뀌지 않았고 같은 테스트가 다시 통과했다.

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| Public evaluation overview page / Anonymous visitor opens the page | 충족 | 다섯 구역 `EvaluationShowcase.tsx:423,541,603,648,696` · 결론과 합성 샘플 notice는 r1과 같음 · 테스트 `EvaluationShowcase.test.tsx:28-40`. 비로그인 리다이렉트 없음은 r1과 같이 미들웨어 matcher 구조(`apps/dashboard/middleware.ts:81`)에 의존 |
| Public evaluation overview page / Navigating between showcases | 충족 | r1과 같음(변경 없음) · 테스트 통과 |
| Evaluation map shows every measurement surface / Measured surface | 충족 | r1과 같음. 근거성 칸 `detail` 문장만 바뀌었고 상태 · 수치 · 분모 · 측정일 · 출처 필드는 그대로이며 `check` 통과 |
| Evaluation map shows every measurement surface / Empty surface | 충족 | r1과 같음 |
| Repetition grid / Known failure across all runs | 충족 | r1과 같음 · 테스트 `EvaluationShowcase.test.tsx:122-` 통과 |
| Repetition grid / Mixed execution paths | 충족 | r1과 같음. 요약표 질의 `name: /회차별 결과/`(`:44`)는 "회차별 거절 결과"와 겹치지 않아 새 행으로 인한 중복 매칭 없음(테스트 통과로 확인) |
| Repetition grid / Partially executed run | 충족 | r1과 같음. 새 거절 표 행도 `answerable_passed/answerable_asked`를 쓰며, `check`가 이 두 값을 not_run을 뺀 칸에서 재집계하므로 미실행이 실패로 세어지지 않는다 |
| Refusal figures shown apart from pass rate / One unanswerable question | 충족 | 통과 28/29 `EvaluationShowcase.tsx:574-581` · 정확한 거절 1/1과 "거절 문항 1개" `:166-169,582-587` · 잘못된 거절 0/29 `:588-595` · "없음" 처리 `:167` · 테스트 `EvaluationShowcase.test.tsx:64-89` |
| Application ledger in date order / Ledger entry rendered | 충족 | r1과 같음(원장 `:648-`) |
| Reproduction conditions and limits stay attached / Limits visible with results | 충족 | r1과 같음(`:696-`) · 거절 표본 수 문구 `:717` |
| Static allowlisted record / Offline rendering | 충족 | r1과 같음 |
| Static allowlisted record / Untrusted record text | 충족 | r1과 같음 |
| Static allowlisted record / Forbidden field in record | 충족 | r1과 같음 · 커밋 파일 검사 통과 |
| Static allowlisted record / Download matches the page | 충족 | r1과 같음. 재export 결과가 커밋된 `evaluation.json`과 동일 |
| Invalid or missing measurements / Series marked invalid | 충족 | 새 행이 `valid` 분기 안에 있음 `:547-549` · 테스트 `EvaluationShowcase.test.tsx:91-120`이 `/회차별/` 표 전부 없음을 단언(거절 표 포함) |
| Invalid or missing measurements / Map and conclusion follow an invalid series | 충족 | r1과 같음 · 테스트 `:111-119` |

### tasks.md 1~3절 인수 조건 대조

| task | 결과 | 비고 |
| --- | --- | --- |
| 1.1 · 1.2 | 충족 | 거절 블록 AC가 스펙의 세 수치로 고쳐졌고 대응 테스트가 있다 |
| 2.1 · 2.2 | 충족 | 변경 없음 |
| 3.1 | 충족 | 0.578 · 0.374가 curated · 공개 기록 · 문서 어디에도 없다 |
| 3.2 | 충족 | 변경 없음 |

## 조치가 필요한 항목

없음.

## 참고 (판정에 영향 없음)

- r1 참고 항목(무효 묶음일 때 원장 · 비용 상세에 남는 반복 측정 수치, 요약표 "경로" 행 대신 열 머리 표시, 결론 문구 차이)은 그대로이며 판정에 영향이 없다.
- 4.1 · 4.2는 아직 `- [ ]`이고, 이 리뷰가 4.1의 일부다. 미완료 task를 완료로 주장한 곳은 없다.
- 스펙 밖에서 사용자가 볼 수 있는 동작이 새로 생긴 곳은 찾지 못했다. 거절 표의 새 행은 스펙 요구 그 자체다.

## 판정 근거

r1의 두 지적이 모두 스펙 범위 안에서 해소됐다. 거절 성능 구역은 회차마다 세 수치를 분모와 함께 보이고 이를 테스트가 단언한다. 출처 미확인 수치는 curated 원본과 공개 기록에서 빠졌고, 재export 결과와 해시가 커밋 파일과 맞는다. 수정은 거절 표 한 행과 curated 문장 한 줄에 그쳐 다른 시나리오의 코드 경로를 건드리지 않았고, 관련 테스트와 `check`를 새로 돌려 통과를 확인했다. 시나리오 16개가 모두 증거와 함께 충족되므로 `pass`다.

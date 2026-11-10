# Spec Conformance 리뷰 — evaluation-experiment-registry r1

- 판정: needs_fix
- 대상: `git diff 5031820..HEAD` (`2a5df56`) + 미커밋 `docs/reference/stack.md`
- 일시: 2026-11-10T13:34:17Z

## 새로 실행한 검증

| 검증 | 결과 |
| --- | --- |
| `supabase/tests/0037_eval_experiments.sql` (로컬 DB, 마지막 rollback) | `0037 eval_experiments: ok` |
| `pytest test_eval_experiment_registry.py test_local_evaluation_server.py test_evidence_research_eval.py` | 39 passed |
| `vitest RegressionDashboard · regression-policy · experiments · LocalEvaluation` | 29 passed, 0 failed |
| 로컬 DB 행 수 조회 | 정책 1 · 기준 세트 1 · 실험 3(`ask-evidence-research` adoption/공개, `ask-replay-reliability` stability/공개, `local-grader-check` grader/비공개) · 결정 1 · `preregistered = f` |
| 등록 upsert SQL을 한 트랜잭션에서 두 번 실행 후 rollback | 실험 3 · 기준 세트 1 · 결정 1 · 정책 1로 그대로 (멱등) |
| 실제 DB에서 `build_snapshot`을 메모리로 두 번 생성 | 두 결과 바이트 동일, 커밋된 `content/experiments.json`과도 바이트 동일, 공개 실험 2개만 포함 |

## 시나리오 판정

### evaluation-experiment-registry

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| Experiment record / Existing results registered without new runs | 충족 | `scripts/eval_experiments.py:168-317`(저장 파일만 읽음, 모델 호출 없음) · `:328-341` · DB 실측 3행 · 테스트 `test_eval_experiment_registry.py:191`, `:221` |
| Experiment record / Unknown run reference | 부분 충족 | 등록 시 검사는 "저장 파일에 `off`/`on`, `run-1`/`run-2`가 있는가"(`eval_experiments.py:174-175`, `:278-279`)와 로컬 기준선 존재(`:310-311`)뿐이다. 실험 행의 `baseline_run_id`/`candidate_run_id` 값 자체를 저장 파일에 대조하는 검사는 내보내기의 `run_identity`(`:407-433`)에만 있다. 실험 정의의 id 문자열과 검사하는 id 집합이 서로 다른 리터럴이라, 실험 정의만 바뀌면 없는 실행 id가 DB에 등록된다. 테스트 `:80`, `:200`, `:233`(저장 파일 누락), `:156`(내보내기 단계) |
| Experiment record / Re-registration is idempotent | 충족 | `eval_experiments.py:348-370` `on conflict (...) do update` · 테스트 `test_eval_experiment_registry.py:98`(SQL 모양) · 위 실측(두 번 upsert 후 행 수 불변) |
| Experiment kinds / Adoption experiment | 충족 | `eval_experiments.py:241-254`(criteria_set_id·policy_version), `:255-266` 결정 · `0037_eval_experiments.sql:69-72` · 테스트 `apps/dashboard/tests/experiments.test.ts:15` |
| Experiment kinds / Stability measurement has no adoption verdict | 충족 (해석 주석 참조) | DB: `eval_experiments.py:275-297`(기준·정책 null), SQL CHECK `0037:69-72`, 결정 금지 `0037:84,90-91`. 측정값: 화면 계산 `RegressionDashboard.tsx:173,348`, 흔들림 명칭 `lib/regression-analysis.ts:74-82` · 테스트 `RegressionDashboard.test.tsx:223-253`, SQL 테스트 `:59-65` |
| Experiment kinds / Grader check has no adoption verdict | **미충족** | 채택 판정 없음(`eval_experiments.py:38-49`)과 판정 변화 수(`RegressionDashboard.tsx:349`)는 있으나, THEN의 "PR 관문 계약 `offline-eval-regression-gate`를 출처로 참조한다"를 만드는 경로가 없다. `LOCAL_EXPERIMENT`·`localGraderExperiment`(`lib/experiments.ts:64-74`)·`eval_experiments` 열 어디에도 이 참조가 없다(저장소 grep 결과 `scripts/check_eval_regression.py:2` 주석뿐) |
| Adoption policy v1 / No improvement means not adoptable | 충족 | `lib/regression-policy.ts:53-61` · 테스트 `regression-policy.test.ts:52` |
| Adoption policy v1 / Single question regression blocks | 충족 | `regression-policy.ts:34-41` · 테스트 `regression-policy.test.ts:38`(재검색 39=39, 회귀 1 → 채택 불가), `:63` |
| Adoption policy v1 / Mismatched conditions | 충족 | `regression-policy.ts:31-32`(problems 반환) · `lib/regression-analysis.ts:106-132`(조건·문항 집합 불일치 사유) · 테스트 `regression-policy.test.ts:93`(조건), `RegressionDashboard.test.tsx:33`(문항 집합) |
| Criteria provenance / Original criteria judged from stored checks | 충족 | `eval_experiments.py:180-227`(`checks` 복사, `adopted` 대조) · 커밋된 스냅샷 조건값 확인(답변 복구·통과 증가·비용 false, 나머지 true, adopted false) · 테스트 `test_eval_experiment_registry.py:41`, `:87` |
| Criteria provenance / Criteria recorded after the runs | 충족 | 생성 열 `0037:43` · `git_first_commit` `eval_experiments.py:146-161` · DB `preregistered = f`(0f9bbbe 02:00Z > 23:26Z) · 테스트 SQL `:41-56`, pytest `:66`, `:74` |
| Criteria provenance / Reference verdict under policy v1 | 충족 | `RegressionDashboard.tsx:513-537`(공식 판정과 분리된 참고 문구, 공식 배지는 `criteria.adopted` 저장값 `:237-243`) · 테스트 `RegressionDashboard.test.tsx:184-198`, `:305-319` |
| Decision record / Research experiment decision | 충족 | `eval_experiments.py:255-266` · 스냅샷 rationale "3개 미충족(...) ... 기본 OFF를 유지 ... 미채택", `criteria_set_id = ask-evidence-research-d4` · 테스트 `test_eval_experiment_registry.py:52-54` |
| Decision record / Measurement experiment decision rejected | 충족 | 복합 외래키 `0037:84,90-91` · SQL 테스트 `:59-74`, 종류 변경 차단 `:109-116` |
| Project-level storage boundary / Anonymous access | 충족 | `0037:99-107`(RLS, 권한 회수) · SQL 테스트 `:136-152`(읽기·쓰기 42501) |
| Project-level storage boundary / Authenticated member access | 충족 | `0037:105-107` · SQL 테스트 `:154-174`(4개 테이블 읽기, 결정 수정 모두 42501), `:177-186`(결정 불변) |
| Public snapshot export / Local-only experiment excluded | 충족 | `eval_experiments.py:464`, `:496-500` · 실측: DB에 `local-grader-check`가 있는 상태에서 내보낸 스냅샷에 공개 실험 2개만 · 테스트 `test_eval_experiment_registry.py:117`, `:131` |
| Public snapshot export / Forbidden field | 충족 | `eval_experiments.py:121`, `:436-460`, 검증이 쓰기 전(`:502`, `:519-521`) · 테스트 `:141`, `:149` |
| Public snapshot export / Deterministic export | 충족 | `eval_experiments.py:506-507`(sort_keys, 고정 들여쓰기, 시각 미포함), `utc()` 정규화 `:138-143` · 테스트 `:163` · 실측 바이트 동일 |
| Single source for adoption thresholds / Threshold drift detected | 충족 | `scripts/evidence_research_eval.py` `COST_LIMIT_RATIO`·`P95_LIMIT_MS` · 테스트 `test_eval_experiment_registry.py:172`(커밋 스냅샷 ↔ 스크립트 상수·`POLICY_V1`), `:184`(화면 하드코딩 흔적), `regression-policy.test.ts:74`(정책 값을 바꾸면 판정이 따라 바뀜). 실패 시 pytest/vitest 단언 위치가 어긋난 곳을 보고 |

### regression-workbench

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| Static experiment snapshot only / Offline rendering | 충족 | `app/showcase/regression/page.tsx:5` `force-static` · `lib/experiments.ts:1`(JSON import) · 로컬 패널은 `onLocal`일 때만(`RegressionDashboard.tsx:1085-1093`), `GoldenJudgePanel`은 개발 모드 외 `null`(`GoldenJudgePanel.tsx:224,261`) · 테스트 `RegressionDashboard.test.tsx:173` |
| Static experiment snapshot only / Untrusted snapshot text | 충족 (테스트 없음) | 스냅샷 문자열은 React 텍스트 노드로만 렌더링(`RegressionDashboard.tsx:503-506` rationale), `dangerouslySetInnerHTML` 없음. 단, 스냅샷 `title`·`rationale`에 HTML을 넣고 글자 그대로 보이는지 확인하는 테스트가 없다 |
| Experiments and local tools are separated / Public visitor | 충족 | `RegressionDashboard.tsx:967-968`, `:1006-1060` · 테스트 `RegressionDashboard.test.tsx:173-183` |
| Experiments and local tools are separated / Local run drawer placement | 충족 | `RegressionDashboard.tsx:1085-1093`(내 검증일 때만, `main` 첫 자식) · 테스트 `RegressionDashboard.test.tsx:143-161` |
| Compared run identity and roles / Research experiment roles | 충족 | 역할은 실험 기록에서(`lib/regression-data.ts:26-33`), 표시 `RegressionDashboard.tsx:437-455`, `runIdentity` `:313-320` · 테스트 `RegressionDashboard.test.tsx:95-99` |
| Adoption experiment verdict / Research verdict by original criteria | 충족 | `RegressionDashboard.tsx:225-235`, `:461-475` · 테스트 `RegressionDashboard.test.tsx:90-111`, `:119` |
| Adoption experiment verdict / Provenance shown honestly | 충족 | `RegressionDashboard.tsx:486-497`(문구와 두 시각) · 테스트 `RegressionDashboard.test.tsx:112-118` |
| Adoption experiment verdict / Policy v1 reference | 충족 | `RegressionDashboard.tsx:513-537` · 테스트 `RegressionDashboard.test.tsx:194-196`, `:307-309` |
| Measurement experiments / Stability measurement | 충족 | `RegressionDashboard.tsx:336-406`, `:802-807` · 테스트 `RegressionDashboard.test.tsx:223-253` |
| Measurement experiments / Grader check in development | 부분 충족 | 배지 없음·판정 변화 수는 구현·테스트됨(`RegressionDashboard.tsx:349`, 테스트 `:162-170`). THEN 후반 "판정 변화가 없으면 ... 정상이라는 설명"은 코드 경로가 있으나(`RegressionDashboard.tsx:376-381`) 판정 변화 0개 상태를 렌더링해 이 문구를 확인하는 테스트가 없다 |
| Read-only policy view / No threshold input | 충족 | `RegressionDashboard.tsx:808-859`(읽기 전용 목록, 입력 없음) · 테스트 `RegressionDashboard.test.tsx:124-126`, `:297`, `:305-319` |
| Read-only policy view / Stale browser values ignored | 충족 | 컴포넌트에 `localStorage` 없음 · 테스트 `RegressionDashboard.test.tsx:285-304`, `test_eval_experiment_registry.py:184` |
| Snapshot download matches the page / Download | 충족 | `app/showcase/regression/experiments.json/route.ts:1-12` · 링크 `RegressionDashboard.tsx:890-898` · 테스트 `experiments.test.ts:7-13` |

## 조치가 필요한 항목

1. **채점 검증 실험에 `offline-eval-regression-gate` 출처 참조가 없다** — 근거 Scenario: "로컬 재채점 이력을 채점 검증으로 등록한다 → ... PR 관문 계약 `offline-eval-regression-gate`를 출처로 참조한다". 현재 실험 기록(`scripts/eval_experiments.py:38-49`), DB 열(`0037_eval_experiments.sql:53-76`), 화면 정의(`apps/dashboard/lib/experiments.ts:64-74`) 어디에도 이 참조가 없다. 제안: 실험 기록에 출처 참조를 넣는다(예: `eval_experiments`에 nullable `source_spec text` 열 또는 grader에만 허용하는 CHECK). 등록 행과 `localGraderExperiment`에 `openspec/specs/offline-eval-regression-gate/spec.md`를 넣고, 내 검증 화면에 출처로 보인다. pytest(등록 행)와 SQL 또는 vitest 단언을 추가한다. 열을 추가하면 design D2의 열 목록도 함께 고친다.

2. **등록 시 실행 id 검사가 실험 행의 id에 묶여 있지 않다** — 근거 Scenario: "실험이 저장 결과에 없는 실행 id를 기준선이나 후보로 지정한다 → 등록이 실패하고 해당 실험은 기록되지 않는다". 지금은 저장 파일에 고정 id 집합이 있는지만 본다(`eval_experiments.py:174-175`, `:278-279`). 실험 정의의 `baseline_run_id`/`candidate_run_id`를 그 파일과 대조하는 검사는 내보내기(`run_identity`, `:407-433`)에만 있다. 제안: `build_records`에서 실험마다 `run_source`별 저장 파일로 두 id의 존재를 검사하고(research·reliability는 `run_identity` 재사용, local은 `local_records`의 실행 목록 사용), 없으면 `RegistryError`를 낸다. 실험 행의 id를 바꾼 경우 등록이 실패하는 pytest를 추가한다.

3. **완료 표시된 시나리오 중 테스트가 없는 두 경로** — (a) Untrusted snapshot text: 스냅샷의 실험 제목·결정 근거에 `<script>`/`<b>` 같은 HTML을 넣은 가짜 스냅샷으로 렌더링해 글자 그대로 보이는지 확인하는 vitest가 없다. (b) Grader check in development: 판정 변화 0개일 때 "채점 규칙을 바꾸지 않았다면 같은 결과가 정상입니다"가 보이는지 확인하는 테스트가 없다(`RegressionDashboard.tsx:376-381`). 제안: 두 경우 모두 `RegressionDashboard.test.tsx`에 단언을 추가한다. (b)는 같은 rows를 가진 두 rescore 실행을 fetch 모의로 넘기면 된다.

4. **(MUST, 현 데이터 영향 없음) 기준 출처 시각을 확인할 수 없을 때의 기록 경로가 없다** — Requirement 본문: "출처 시각이 실행보다 늦거나 확인할 수 없으면 사전 등록이라고 표시하면 안 되며, 그 사실을 기록해야 MUST 한다". 지금은 커밋을 찾지 못하면 등록이 실패한다(`eval_experiments.py:159-160`). `source_first_commit_at`도 `not null`이다(`0037:40`). 거짓 사전 등록은 생기지 않지만 "확인할 수 없음"을 기록하는 경로가 없다. 제안: 이 경로를 구현한다(nullable 시각, 생성 열이 null이면 false, 화면 문구 "기록 시점 확인 불가"). 실패를 의도한 설계라면 스펙 문구를 "등록을 거부한다"로 맞추고 사람의 확인을 받는다.

## 관찰 (판정에 반영하지 않음)

- **측정값의 "기록" 해석**: Experiment kinds 시나리오의 "측정값으로 기록된다"는 문자 그대로 읽으면 DB나 스냅샷 저장을 뜻할 수 있다. 하지만 design D1과 Non-Goals는 측정값을 DB에 저장하지 않고 화면이 계산한다고 명시한다. 같은 Requirement가 "흔들림으로 ... 기록해야"처럼 '기록'을 명명·표시의 뜻으로도 쓰고 있어 화면 계산을 충족으로 판정했다. sync 전에 delta spec 문구를 "측정값으로 계산·표시된다"로 다듬으면 이후 해석 분쟁을 줄일 수 있다.
- **Ask 반복 측정의 실행 시각**: Requirement "Compared run identity and roles"는 실행 시각 표시를 MUST로 둔다. `evaluation-runs.json`에 시각이 없어(`eval_experiments.py:430-431` 주석) 화면에서는 시각 없이 id·리비전만 보인다. 시나리오는 재검색만 다루므로 판정에서는 뺐다. 추측한 값을 넣지 않은 것은 맞다. 다만 "실행 시각 기록 없음"을 명시하면 요구와 더 정확히 맞는다.
- **화면의 실행 식별 정보 출처**: design D4는 실행 id·리비전·시각을 스냅샷에서 그대로 표시한다고 했다. 화면 `runIdentity`는 `regression-data.ts`가 기존 공개 기록에서 읽은 값을 쓴다(`regression-data.ts:47-51`). 스냅샷의 `experiments[].runs`는 화면이 읽지 않는다. 값은 같지만 design과 다르다.
- **페이지 메타데이터**: `app/showcase/regression/page.tsx:7-9`의 `<title>`과 description에 "회귀"가 남아 있다. 측정 실험 화면 본문(`main`)에는 없고(테스트 `RegressionDashboard.test.tsx:246`), 스펙은 질문별 변화의 명칭만 규정하므로 위반으로 보지 않았다.
- **`docs/reference/stack.md`**: `0037`(로컬 검증, 운영 미적용)을 기록한 미커밋 변경은 task 5.1 요구와 맞다. 같은 파일의 "현재 테이블 15개" 목록에는 새 테이블 4개가 빠져 있다. 스펙 판정 대상은 아니다.
- **task 1.1 AC 문구**: AC는 "`anon`·`authenticated`는 0행"이라고 쓰지만, 수정된 delta spec과 구현은 42501 거부다. 스펙이 정본이라 판정에는 영향이 없다. tasks.md AC 문구만 남아 있다.

## 판정 근거

delta spec 33개 시나리오(evaluation-experiment-registry 20 · regression-workbench 13) 중 30개는 코드 경로와 테스트(또는 이번 실측)로 충족된다(Untrusted snapshot text는 구조적으로 충족하나 테스트 없음). 한 시나리오(Grader check has no adoption verdict)는 THEN의 `offline-eval-regression-gate` 출처 참조를 만드는 경로가 아예 없어 미충족이다. 두 시나리오(Unknown run reference, Grader check in development)는 부분 충족이다. task 4.1과 1.1이 `- [x]`로 완료 표시된 상태라 조용한 범위 축소와 미검증 완료 주장에 해당한다. 네 조치 항목 중 1~3은 스펙 범위 안에서 코드·테스트만 고치면 해결되고, 스펙을 바꿀 필요가 없으므로 `needs_fix`로 판정한다. 4는 구현으로 해결하는 것이 기본안이다. 설계 의도가 등록 거부라면 그때만 스펙 문구 수정에 사람의 확인이 필요하다.

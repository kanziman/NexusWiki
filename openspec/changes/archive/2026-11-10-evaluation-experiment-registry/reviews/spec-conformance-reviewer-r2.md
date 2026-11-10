# Spec Conformance 리뷰 — evaluation-experiment-registry r2

- 판정: pass
- 대상: `git diff 5031820..HEAD` (`9d59cdc`), r1 이후 수정 `git show 9d59cdc`
- 일시: 2026-11-10T13:40:03Z

## 새로 실행한 검증

| 검증 | 결과 |
| --- | --- |
| `supabase/tests/0037_eval_experiments.sql` (로컬 DB, 마지막 rollback) | `0037 eval_experiments: ok`, 종료 코드 0 |
| `pytest test_eval_experiment_registry.py test_local_evaluation_server.py test_evidence_research_eval.py` | 42 passed |
| `vitest RegressionDashboard · regression-policy · experiments · LocalEvaluation` | 31 passed, 0 failed |
| `openspec validate evaluation-experiment-registry --strict` | valid |
| 로컬 DB 행 조회 | 실험 3. `local-grader-check`(grader, 비공개)만 `reference = openspec/specs/offline-eval-regression-gate/spec.md`, 나머지 둘은 null. 기준 세트 `0f9bbbe` · `2026-11-09 02:00:01+00` · `preregistered = f`. 결정 1 |
| `build_records()` → upsert SQL을 한 트랜잭션에서 두 번 실행 후 rollback | 실험 3 · 기준 세트 1 · 결정 1 · 정책 1로 그대로(멱등, 새 `reference` 열 포함) |
| 실제 DB에서 `build_snapshot`을 메모리로 두 번 생성 | 두 결과 바이트 동일, 커밋된 `content/experiments.json`과도 바이트 동일, 공개 실험 2개(`ask-evidence-research`, `ask-replay-reliability`)만 포함 |

## r1 조치 항목 해소 여부

| r1 항목 | 결과 | 증거 |
| --- | --- | --- |
| 1. 채점 검증에 `offline-eval-regression-gate` 출처 참조 없음 | 해소 | 열 `supabase/migrations/0037_eval_experiments.sql:69`, grader면 필수 CHECK `:71` · 등록 행 `scripts/eval_experiments.py:49` · 허용 필드 `:117` · 화면 정의 `apps/dashboard/lib/experiments.ts:57,77` · 화면 표시 `components/RegressionDashboard.tsx:406` · 테스트: SQL `supabase/tests/0037_eval_experiments.sql:72-78`(출처 없는 grader 거부), pytest `test_eval_experiment_registry.py:238`(화면 정의와 대조), `:281`(경로 실재), vitest `RegressionDashboard.test.tsx:178-180` · DB 실측 행 |
| 2. 등록 시 실행 id 검사가 실험 행에 묶여 있지 않음 | 해소 | `scripts/eval_experiments.py:351`에서 upsert 전에 `validate_run_refs`(`:355-361`)가 실험 행마다 `run_identity`(`:427-453`)로 두 id를 저장 파일과 대조한다. 없으면 `RegistryError`이고 `main`이 psql에 도달하지 않는다(`:536-537`). `local`은 `local_records`가 디렉터리 목록에서 id를 고르고 기준선이 목록에 있는지 검사하므로(`:315-322`) 구조적으로 존재가 보장된다 · 테스트 `test_eval_experiment_registry.py:268`(실험 행 id를 `run-9`로 바꾸면 등록 실패) |
| 3a. Untrusted snapshot text 테스트 없음 | 해소 | `RegressionDashboard.test.tsx:329-340`(결정 근거에 `<img onerror>`, 기준 이름에 `<b>`를 넣고 글자 그대로 보이며 `main img`가 없음을 확인) |
| 3b. 판정 변화 0일 때 정상 설명 테스트 없음 | 해소 | 코드 `RegressionDashboard.tsx:378-383` · 테스트 `RegressionDashboard.test.tsx:173-177` |
| 4. 기준 출처 시각을 확인할 수 없을 때 기록 경로 없음 | 해소 | `git_first_commit`이 못 찾으면 `(None, None)`(`eval_experiments.py:164-165`) · 열 nullable `0037:39-41`, 생성 열은 null이면 null `:45` · 스냅샷 null 보존 `eval_experiments.py:499-500` · 화면 "기록 시점을 확인할 수 없음 · 사전 등록으로 표시하지 않음"과 "기준 출처의 커밋 기록 없음" `RegressionDashboard.tsx:490-506` · 테스트 pytest `:255`, SQL `0037 test:58-67`, vitest `RegressionDashboard.test.tsx:341-361` |

스펙 문구 두 곳(측정값은 "화면이 계산해 보인다", authenticated는 `42501` 거부)은 r1 관찰을 해소하는 방향이다. 구현과 맞고 다른 시나리오와도 모순되지 않는다. design D2(nullable 출처 시각·`reference` 열)와 D4(화면은 `regression-data.ts`에서 같은 값을 읽음)도 구현과 일치한다. tasks.md 1.1 AC의 "0행" 문구도 "42501 거부"로 맞춰졌다.

## 시나리오 판정

### evaluation-experiment-registry

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| Experiment record / Existing results registered without new runs | 충족 | `eval_experiments.py:173-327`(저장 파일만 읽고 모델 호출 없음), `:338-352` · DB 실측 3행 · 테스트 `test_eval_experiment_registry.py:191`, `:221` |
| Experiment record / Unknown run reference | 충족 | `eval_experiments.py:351`, `:355-361`, `:431-432`, `:443-444` · 테스트 `test_eval_experiment_registry.py:268` |
| Experiment record / Re-registration is idempotent | 충족 | `eval_experiments.py:368-390` `on conflict ... do update` · 테스트 `test_eval_experiment_registry.py:98` · 위 두 번 upsert 실측 |
| Experiment kinds / Adoption experiment | 충족 | `eval_experiments.py:249-275` · `0037:72-76`(도입 실험 CHECK) · 테스트 `experiments.test.ts:15` |
| Experiment kinds / Stability measurement has no adoption verdict | 충족 | 기준·정책 null `eval_experiments.py:284-307` · 결정 금지 복합 외래키 `0037:95-99` · 화면 계산 `RegressionDashboard.tsx:168-173`, `:348-351`, `:377-389` · 테스트 `RegressionDashboard.test.tsx:223-253`, SQL 테스트 |
| Experiment kinds / Grader check has no adoption verdict | 충족 | 채택 판정 없음 `eval_experiments.py:38-50` · 판정 변화 수 `RegressionDashboard.tsx:351` · 출처 참조 `0037:69-71`, `eval_experiments.py:49` · 테스트 위 r1 항목 1 |
| Adoption policy v1 / No improvement means not adoptable | 충족 | `lib/regression-policy.ts:53-61` · 테스트 `regression-policy.test.ts:52` |
| Adoption policy v1 / Single question regression blocks | 충족 | `regression-policy.ts:34-41` · 테스트 `regression-policy.test.ts:38`, `:63` |
| Adoption policy v1 / Mismatched conditions | 충족 | `regression-policy.ts:31-32` · `lib/regression-analysis.ts:106-132` · 테스트 `regression-policy.test.ts:93`, `RegressionDashboard.test.tsx:33` |
| Criteria provenance / Original criteria judged from stored checks | 충족 | `eval_experiments.py:185-232` · 커밋 스냅샷 조건값 · 테스트 `test_eval_experiment_registry.py:41`, `:87` |
| Criteria provenance / Criteria recorded after the runs | 충족 | 생성 열 `0037:45` · DB `preregistered = f` · 화면 `RegressionDashboard.tsx:492-493` · 테스트 SQL, pytest `:66`, `:74` |
| Criteria provenance / Reference verdict under policy v1 | 충족 | 참고 문구는 공식 판정과 분리, 공식 배지는 `criteria.adopted` 저장값(`RegressionDashboard.tsx:237-243`) · 테스트 `RegressionDashboard.test.tsx:184-198`, `:305-319` |
| Decision record / Research experiment decision | 충족 | `eval_experiments.py:264-275` · 테스트 `test_eval_experiment_registry.py:52-54` |
| Decision record / Measurement experiment decision rejected | 충족 | `0037:95-99` · SQL 테스트(측정 실험 결정 삽입 실패, 종류 변경 차단) |
| Project-level storage boundary / Anonymous access | 충족 | RLS·권한 회수 `0037` · SQL 테스트(읽기·쓰기 42501, TRUNCATE 거부 `0037 test:172-178`) |
| Project-level storage boundary / Authenticated member access | 충족 | SQL 테스트(4개 테이블 읽기·결정 수정 42501, TRUNCATE 거부 `0037 test:200-206`, 결정 불변) |
| Public snapshot export / Local-only experiment excluded | 충족 | `eval_experiments.py:484`, `:517-521` · 실측(DB에 `local-grader-check`가 있어도 공개 2개만) · 테스트 `test_eval_experiment_registry.py:117`, `:131` |
| Public snapshot export / Forbidden field | 충족 | `eval_experiments.py:123`, `:456-479`, 쓰기 전 검증 `:523`, `:541-542` · 테스트 `:141`, `:149` |
| Public snapshot export / Deterministic export | 충족 | `eval_experiments.py:527-528` · 테스트 `:163` · 실측 바이트 동일 |
| Single source for adoption thresholds / Threshold drift detected | 충족 | `scripts/evidence_research_eval.py` 상수를 `eval_experiments.py:183-184`가 읽음 · 테스트 `test_eval_experiment_registry.py:172`, `:184`, `regression-policy.test.ts:74` |

### regression-workbench

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| Static experiment snapshot only / Offline rendering | 충족 | `app/showcase/regression/page.tsx:5` `force-static` · `lib/experiments.ts` JSON import · 테스트 `RegressionDashboard.test.tsx:173`(공개 렌더) |
| Static experiment snapshot only / Untrusted snapshot text | 충족 | React 텍스트 노드로만 렌더링 · 테스트 `RegressionDashboard.test.tsx:329-340` |
| Experiments and local tools are separated / Public visitor | 충족 | 테스트 `RegressionDashboard.test.tsx:182-` (공개 배포에 로컬 개발 도구 구역 없음) |
| Experiments and local tools are separated / Local run drawer placement | 충족 | 테스트 `RegressionDashboard.test.tsx:143-161` |
| Compared run identity and roles / Research experiment roles | 충족 | `RegressionDashboard.tsx:313-322`(재검색은 `createdAt`이 있어 시각 표시, 수정 영향 없음) · 테스트 `RegressionDashboard.test.tsx:95-99` |
| Adoption experiment verdict / Research verdict by original criteria | 충족 | `RegressionDashboard.tsx:225-235` · 테스트 `RegressionDashboard.test.tsx:90-111` |
| Adoption experiment verdict / Provenance shown honestly | 충족 | `RegressionDashboard.tsx:490-506`(`preregistered === false` 분기 문구와 두 시각, 수정 후에도 유지) · 테스트 `RegressionDashboard.test.tsx:112-118` |
| Adoption experiment verdict / Policy v1 reference | 충족 | 테스트 `RegressionDashboard.test.tsx:194-196`, `:307-309` |
| Measurement experiments / Stability measurement | 충족 | `RegressionDashboard.tsx:338-408` · 테스트 `RegressionDashboard.test.tsx:223-253` |
| Measurement experiments / Grader check in development | 충족 | `RegressionDashboard.tsx:345-351`, `:378-383` · 테스트 `RegressionDashboard.test.tsx:162-180` |
| Read-only policy view / No threshold input | 충족 | 테스트 `RegressionDashboard.test.tsx:124-126`, `:297`, `:305-319` |
| Read-only policy view / Stale browser values ignored | 충족 | 테스트 `RegressionDashboard.test.tsx:285-304`, `test_eval_experiment_registry.py:184` |
| Snapshot download matches the page / Download | 충족 | `app/showcase/regression/experiments.json/route.ts` · 테스트 `experiments.test.ts:7-13` |

## 조치가 필요한 항목

없음.

## 관찰 (판정에 반영하지 않음)

- **"실행 시각 기록 없음" 표시에 테스트가 없다**: `RegressionDashboard.tsx:317-319`는 Ask 반복 측정처럼 시각이 없는 실행에 이 문구를 보인다. 커밋 메시지는 이 표시도 테스트했다고 쓰지만 `tests/`에는 이 문자열을 단언하는 테스트가 없다. Requirement "Compared run identity and roles" 본문의 MUST와 관련이 있지만, 시나리오는 재검색 실험만 다루므로 판정에서는 뺐다. 원하면 안정성 측정 화면에 단언 하나를 추가하면 된다.
- **Untrusted text 테스트 범위**: 테스트는 결정 근거와 기준 이름에 HTML을 넣는다. 시나리오가 예로 든 "실험 제목"은 넣지 않는다. 같은 텍스트 노드 렌더링 경로이고 시나리오가 "제목이나 결정 근거"라서 충족으로 판정했다.
- **결정 날짜 출처가 없을 때 등록 중단**: `eval_experiments.py:235-237`은 결과 기록의 커밋을 찾지 못하면 등록을 멈춘다. 이것은 기준 출처 시각(Requirement가 "기록"을 요구하는 대상)이 아니라 결정 날짜에 관한 동작이다. 날짜를 지어내지 않는 쪽이 맞다. 스펙 위반은 아니다.
- **`local` 실행 id 검사 생략**: `validate_run_refs`가 `local`을 건너뛰는 근거는 `local_records`가 id를 저장 파일 목록에서 직접 고른다는 점이다. `LOCAL_EXPERIMENT`에 고정 실행 id가 생기면 이 근거가 사라지니 그때는 검사를 함께 넣어야 한다.

## 판정 근거

r1의 조치 4건이 모두 코드·스키마·테스트로 해소됐다. 이번 수정은 nullable 출처 시각, `reference` 열과 grader CHECK, 등록 전 실행 id 대조를 넣었다. 이 수정이 기존 시나리오를 깨뜨리지 않았는지는 새로 실행한 SQL·pytest·vitest와 DB 실측으로 확인했다. 실측 내용은 멱등 upsert, 결정적 스냅샷, 커밋 스냅샷과의 바이트 일치, `preregistered = f` 유지, 공개 실험 2개만 내보냄이다. 바뀐 spec·design 문구는 구현과 일치하고, `openspec validate --strict`도 통과한다. delta spec 33개 시나리오가 모두 증거와 함께 충족되므로 `pass`로 판정한다.

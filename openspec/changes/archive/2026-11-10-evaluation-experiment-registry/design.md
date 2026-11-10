## Context

- 공개 화면 `/showcase/regression`은 `force-static`이며 `apps/dashboard/content/*.json`에 커밋된 공개 기록만 읽는다. 공개 배포는 DB 자격증명이 없다.
- 실행 자체는 DB에 없다. 재검색 OFF/ON은 `content/evidence-research.json`, Ask 반복 측정은 `content/evaluation-runs.json`, 로컬 재채점은 gitignore된 `.worktrees/evaluation-dashboard/run-*.json`에 있다.
- 재검색 실험의 원래 채택 기준은 `openspec/changes/archive/2026-11-09-ask-evidence-research/design.md` D4에 있고, 조건별 판정은 `content/evidence-research.json`의 `checks`·`adopted`로 저장돼 있다. 이 문서가 HEAD 이력에 처음 들어온 커밋은 `0f9bbbe`(2026-11-09 11:00 KST)로, ON 실행(08:53 KST)보다 늦다. squash 전 브랜치 커밋 `8a1800d`(09:43)도 실행보다 늦지만 클론마다 있을 수도 없을 수도 있어 기준으로 쓰지 않는다.
- 비용 ×1.5·p95 15000ms는 `scripts/evidence_research_eval.py`에, 50%·15초 기본값은 `RegressionDashboard.tsx`에 각각 하드코딩돼 있다.
- 운영 DB는 `0035`까지 적용, `0036`은 로컬 검증만 됐다(`docs/reference/stack.md`). 이 change의 마이그레이션은 `0037`이다.
- 같은 브랜치(`codex/golden-answer-judge`)에 다른 작업의 미커밋 변경이 함께 있다. 구현은 별도 브랜치에서 한다.

## Goals / Non-Goals

**Goals:**
- 실험·기준 세트·정책·결정 기록을 프로젝트 전역 테이블 네 개에 정본으로 둔다.
- 판정 계산 로직을 대시보드 TS 한 곳에 두고, 기준값은 스냅샷의 정책에서만 읽는다.
- 공개 페이지는 커밋된 스냅샷만으로 렌더링한다.

**Non-Goals:**
- 새 실행·재채점·모델 호출. 기존 저장 결과만 등록한다.
- 계산한 참고 판정(정책 v1)과 측정값의 DB 저장. 공식 판정(원래 기준)만 저장한다.
- 반복 실행, 평가 세트 버전 관리, 결정 승인 화면과 승인 흐름, 운영 롤아웃·기능 플래그.
- 화면에서 실험·결정을 만들거나 고치는 기능. 등록은 스크립트만 한다.
- 운영(클라우드) DB에 `0037` 적용. 공개 배포는 DB가 필요 없고, 적용은 운영자가 별도로 판단한다.
- `scripts/evidence_research_eval.py`의 판정 의미 변경과 기존 `content/evidence-research.json` 재생성. 상수 이름만 정리한다.
- 아카이브된 `2026-11-09-ask-evidence-research/design.md` 수정.
- 골든셋과 AI 심사 패널(`GoldenJudgePanel`)과 골든셋 리뷰 페이지 변경. 사이드바 위치만 로컬 개발 도구 구역으로 옮긴다.
- 실험 간 연결(반복 측정의 흔들림을 도입 판정에 반영). 화면 문구로만 언급한다.

## Decisions

### D1. 판정은 화면(TS)에서 정책으로 계산한다 (Gate 2 B안)

DB에는 정책·기준 세트·실험·결정만 두고, 정책 v1 참고 판정과 측정값은 대시보드가 스냅샷의 정책 값으로 계산한다. 원래 기준의 조건별 결과는 계산하지 않고 저장값을 기준 세트에 복사한다.

- 기각한 A안(등록 시 Python 계산·저장): 질문 목록 분류가 TS에 남아 회귀 계산이 Python·TS 두 곳이 된다. 지금 생긴 스크립트·화면 판정 불일치가 다시 생긴다.
- 기각한 C안(실험 1행 jsonb 문서): 종류별 규칙(측정 실험의 결정 금지 등)을 CHECK로 강제할 수 없고, 정책 v1이 실험마다 복사돼 버전 참조가 깨진다.

### D2. 테이블 네 개, 모두 전역·`service_role` 전용

`0037_eval_experiments.sql`:

- `eval_policies`: `version text pk`(예: `adoption-v1`), `regression_rule text check (= 'per_question')`, `require_improvement boolean`, `max_excluded int`, `max_cost_increase_pct numeric`, `max_p95_increase_ms int`, `limitation text`, `defined_on date`.
- `eval_criteria_sets`: `id text pk`, `name`, `source_path`, `source_first_commit_at timestamptz`(null 허용), `source_commit text`(null 허용 — 출처 커밋을 찾지 못하면 시각을 지어내지 않고 null로 두며 `preregistered`도 null(확인 불가)이 된다), `earliest_run_at timestamptz`, `preregistered boolean generated always as (source_first_commit_at < earliest_run_at)`, `conditions jsonb`(조건 key·이름·허용값·실제값·충족 여부 배열), `adopted boolean`.
- `eval_experiments`: `id text pk`, `kind text check (in ('adoption','stability','grader'))`, `title`, `question`, `run_source text check (in ('research','reliability','local'))`, `baseline_run_id`, `candidate_run_id`, `baseline_role`, `candidate_role`, `criteria_set_id` → `eval_criteria_sets`, `policy_version` → `eval_policies`, `public boolean`, `reference text`(판정 근거가 되는 다른 계약 경로, 채점 검증은 `openspec/specs/offline-eval-regression-gate/spec.md` 필수), `unique (id, kind)`. CHECK: `kind = 'adoption'`이면 `criteria_set_id`와 `policy_version`이 있어야 하고, 아니면 둘 다 null이어야 한다.
- `eval_decisions`: `experiment_id text pk`, `experiment_kind text check (= 'adoption')`, `foreign key (experiment_id, experiment_kind) references eval_experiments (id, kind)`, `status text check (in ('adopted','not_adopted','deferred'))`, `rationale`, `decided_on date`, `criteria_set_id`.

모든 테이블은 `enable row level security`만 하고 정책을 두지 않는다. 안 그러면 `anon`·`authenticated`가 전역 행을 읽는다. 대신 `revoke all ... from anon, authenticated`를 함께 둔다. `workspace_id` 열은 없다. 실험은 테넌트 데이터가 아니라 프로젝트 운영 기록이다.

- 측정 실험의 결정 금지는 복합 외래키 `(experiment_id, experiment_kind)`와 `experiment_kind = 'adoption'` CHECK로 DB가 강제한다. 트리거보다 단순하고 우회할 수 없다.
- 실행은 파일에 있어서 외래키로 묶을 수 없다. 실행 id 존재 검사는 등록 스크립트가 한다(D3).

### D3. 등록 스크립트: 저장 결과 → DB, 멱등

`scripts/eval_experiments.py register`가 로컬 DB 컨테이너(`supabase_db_NexusWiki`)의 `psql`로 접속해 트랜잭션 안에서 `set local role service_role`로 전환한 뒤 정책 v1, 재검색 원래 기준 세트, 실험 세 개, 재검색 결정을 upsert한다. REST 키를 읽지 않으므로 비밀값이 스크립트나 로그에 들어가지 않고, 쓰기 역할은 여전히 `service_role` 하나다. 같은 파일의 `export`가 D4를 맡는다.

- 실행 id는 `run_source`별 저장 파일에서 존재를 확인하고, 없으면 그 실험을 쓰지 않고 실패한다.
- 원래 기준 세트의 조건별 결과는 `content/evidence-research.json`의 `checks`에서 복사한다. 숫자 허용값(×1.5, 15000ms)은 D4 문서 문구가 아니라 실제 판정을 낸 스크립트 상수에서 가져온다.
- `source_first_commit_at`은 원래 경로와 아카이브 경로를 `git log --follow`로 모두 보고 가장 이른 커밋을 쓴다. `earliest_run_at`은 실행 메타데이터 `created_at`의 최솟값이다.
- 로컬 재채점 실험(`public = false`)은 등록 시점의 서버 기준선과 최신 완료 실행으로 등록한다. 개발 화면은 기존처럼 로컬 실행기의 실시간 실행 목록을 쓰고, 실험 기록에서는 제목·종류·역할만 가져온다.

### D4. 내보내기 스크립트: DB → 허용 필드 스냅샷

`scripts/eval_experiments.py export`가 같은 방식으로 `service_role`로 읽어 `public = true` 실험과 그 참조를 `apps/dashboard/content/experiments.json`으로 쓴다.

- 허용 필드 목록을 코드에 두고, 목록 밖 필드나 금지 이름(`workspace_id`, `user_id`, `answer` 등)이 있으면 쓰기 전에 실패한다.
- 키 정렬, 고정 들여쓰기, 내보낸 시각 미포함으로 같은 DB 상태에서 같은 바이트를 낸다.
- 실행의 id·리비전·실행 시각을 스냅샷 `runs`에 넣어 내려받는 사람이 기존 기록 없이도 실행을 짚을 수 있게 한다. 화면은 같은 값을 기존 공개 기록(`regression-data.ts`)에서 읽는다. 두 값은 같은 원본에서 나오며, 실행 시각이 없는 기록은 "실행 시각 기록 없음"으로 보인다.
- `/showcase/regression/experiments.json` 정적 라우트가 같은 파일을 내려준다. 기존 `evaluation/results.json` 라우트와 같은 방식이다.

### D5. 화면: 기존 계산을 유지하고 정책 평가 함수를 더한다

- `lib/regression-analysis.ts`의 `compareRuns`는 질문 분류를 그대로 맡는다. `evaluatePolicy(analysis, policy)`를 추가해 정책 v1 조건별 결과를 낸다. 기준값 인자는 정책 객체에서만 받는다.
- 도입 실험: 공식 판정은 기준 세트의 저장값으로 그린다. 정책 v1 결과는 공식 판정과 다른 경우에만 참고 문구로 보인다.
- 측정 실험: 안정성은 질문별 판정 일치 수(두 실행 모두 측정된 질문 중 통과 여부가 같은 수)와 흔들린 질문, 채점 검증은 판정이 바뀐 질문 수를 보인다.
- 도입 실험은 등록된 기준선·후보 쌍으로 고정한다. 실행 선택과 맞바꾸기는 측정 실험에만 남긴다. 맞바꾸면 공식 판정(저장값)과 질문 목록(계산값)이 서로 다른 쌍을 말하게 되기 때문이다.
- 허용 기준 입력칸, `ReviewPanel`, 기준·메모 localStorage 읽기·쓰기를 삭제한다. 남은 저장값은 읽지 않고 그대로 둔다. 지우는 코드를 넣지 않아 방문자 저장소를 건드리지 않는다.
- 사이드바는 「실험」과 「로컬 개발 도구」(개발 모드만) 두 구역이다. 실행 서랍(`LocalEvaluationPanel`)은 로컬 실험 화면 맨 위에서만 렌더링하고, 다른 실험의 "이 컴퓨터에 저장된 검사 기록" 안내는 없앤다.

### D6. 기준값 정본과 어긋남 검사

- `scripts/evidence_research_eval.py`의 ×1.5·15000은 이름 있는 상수로 바꾸고, pytest가 그 값이 등록된 원래 기준 세트의 허용값과 같은지 확인한다.
- 대시보드에는 기준 숫자를 두지 않는다. Vitest가 정책 값을 바꾼 가짜 스냅샷으로 판정이 따라 바뀌는지 확인해, 하드코딩이 남으면 실패하게 한다.

## Risks / Trade-offs

- [화면이 계산한 참고 판정이 DB에 없다] → 공식 판정과 결정은 DB에 있다. 참고 판정은 화면에 "참고"로만 표시하고, 저장이 필요해지면 판정 테이블을 추가한다.
- [로컬 재채점 실험은 실행이 계속 늘어 기록과 화면의 쌍이 어긋날 수 있다] → 로컬 실험은 공개되지 않고, 개발 화면은 실행기의 실시간 기준선을 쓴다고 문서화한다.
- [사전 등록을 증명하지 못한다는 표시가 인상을 나쁘게 할 수 있다] → 사실대로 표시하는 것 자체가 이 페이지의 핵심 주장이다. 두 시각을 함께 보여 준다.
- [운영 DB에 `0037`이 없다] → 공개 배포는 스냅샷만 읽어 영향이 없다. 운영 적용 여부는 이 change 밖에서 결정한다.
- [다른 작업과 같은 파일(`RegressionDashboard.tsx`, `LocalEvaluationPanel.tsx`)을 건드린다] → 구현 전에 오늘 세션의 화면 수정과 골든셋 작업을 브랜치·커밋 단위로 나눈 뒤 시작한다.

## Migration Plan

1. 로컬: `supabase db reset` 또는 `migration up`으로 `0037`을 적용한다(포트 544xx).
2. 등록 → 내보내기를 실행하고 `content/experiments.json`을 커밋한다.
3. 배포는 정적 페이지만 바뀐다. 롤백은 커밋 되돌리기로 충분하다. 테이블은 공개 경로가 읽지 않으므로 남아도 무해하다.

-- =============================================================================
-- NexusWiki 0037: 평가 실험 · 판정 기준 · 채택 정책 · 결정 기록
--
-- 관련 이슈: #272, #273
-- 설계 근거: openspec/changes/evaluation-experiment-registry/design.md > D2
-- 계약:     openspec/changes/evaluation-experiment-registry/specs/evaluation-experiment-registry/spec.md
--
-- 실험은 테넌트 데이터가 아니라 프로젝트 운영 기록이다. workspace_id가 없고, 등록·내보내기
-- 스크립트가 service_role로만 읽고 쓴다. 공개 화면은 이 테이블을 읽지 않고 커밋된 스냅샷만 읽는다.
--
-- ⚠️ 네 테이블 모두 RLS를 켜고 정책을 두지 않는다. 정책을 하나라도 추가하면 anon·authenticated가
--    프로젝트 전역 행을 읽게 된다. 운영(클라우드) 적용은 이 change 밖에서 결정한다.
-- =============================================================================

begin;

-- -----------------------------------------------------------------------------
-- 1. 채택 정책: 이후 도입 실험의 기본 기준. 버전마다 한 행이며 고치지 않고 새 버전을 더한다.
-- -----------------------------------------------------------------------------
create table public.eval_policies (
  version               text primary key check (version ~ '^[a-z0-9]+(-[a-z0-9]+)*$'),
  -- 질문 단위만 허용한다. 합계 기준을 다시 허용하면 한 질문의 회귀를 다른 질문의 개선이 가린다.
  regression_rule       text not null check (regression_rule = 'per_question'),
  require_improvement   boolean not null,
  max_excluded          integer not null check (max_excluded >= 0),
  max_cost_increase_pct numeric not null check (max_cost_increase_pct >= 0),
  max_p95_increase_ms   integer not null check (max_p95_increase_ms >= 0),
  limitation            text not null check (length(limitation) > 0),
  defined_on            date not null
);

-- -----------------------------------------------------------------------------
-- 2. 기준 세트: 한 실험을 실제로 판정한 조건과 그 출처. 조건별 결과는 계산하지 않고 당시 저장값을 옮긴다.
-- -----------------------------------------------------------------------------
create table public.eval_criteria_sets (
  id                     text primary key check (id ~ '^[a-z0-9]+(-[a-z0-9]+)*$'),
  name                   text not null,
  source_path            text not null,
  -- 출처 커밋을 찾지 못하면 null이다. 지어낸 시각을 넣으면 사전 등록 여부가 거짓이 된다.
  source_commit          text check (source_commit ~ '^[0-9a-f]{7,40}$'),
  source_first_commit_at timestamptz,
  earliest_run_at        timestamptz not null,
  -- 손으로 쓰지 못하게 생성 열로 둔다. 쓸 수 있으면 결과를 본 뒤 정한 기준도 사전 등록으로 표시된다.
  -- 출처 시각이 null이면 null(확인 불가)이고, 화면은 이를 사전 등록으로 표시하지 않는다.
  preregistered          boolean generated always as (source_first_commit_at < earliest_run_at) stored,
  conditions             jsonb not null check (
                           jsonb_typeof(conditions) = 'array' and jsonb_array_length(conditions) > 0
                         ),
  adopted                boolean not null
);

-- -----------------------------------------------------------------------------
-- 3. 실험: 목적 · 종류 · 기준선과 후보. 실행은 파일에 있어 외래키로 묶지 못하므로 등록 스크립트가 존재를 검사한다.
-- -----------------------------------------------------------------------------
create table public.eval_experiments (
  id               text primary key check (id ~ '^[a-z0-9]+(-[a-z0-9]+)*$'),
  kind             text not null check (kind in ('adoption', 'stability', 'grader')),
  title            text not null,
  question         text not null,
  run_source       text not null check (run_source in ('research', 'reliability', 'local')),
  baseline_run_id  text not null,
  candidate_run_id text not null,
  baseline_role    text not null,
  candidate_role   text not null,
  criteria_set_id  text references public.eval_criteria_sets (id) on delete restrict,
  policy_version   text references public.eval_policies (version) on delete restrict,
  public           boolean not null,
  -- 판정 근거가 되는 다른 계약(예: 채점 검증의 PR 관문 스펙 경로).
  reference        text,
  -- 채점 검증은 PR 관문 계약을 따른다. 출처가 없으면 판정 변화의 의미를 화면이 설명할 수 없다.
  constraint eval_experiments_grader_reference check (kind <> 'grader' or reference is not null),
  -- 같은 실행끼리의 비교는 변화가 0으로 나와 성과처럼 보인다.
  constraint eval_experiments_distinct_runs check (baseline_run_id <> candidate_run_id),
  -- 채택 판정 근거는 도입 실험에만 있다. 측정 실험에 기준이 붙으면 화면이 채택 배지를 그린다.
  constraint eval_experiments_adoption_refs check (
    (kind = 'adoption' and criteria_set_id is not null and policy_version is not null)
    or (kind <> 'adoption' and criteria_set_id is null and policy_version is null)
  ),
  -- 결정 기록의 복합 외래키 대상. 결정이 다른 종류의 실험이나 다른 기준 세트를 가리키지 못하게 한다.
  unique (id, kind),
  unique (id, criteria_set_id)
);

-- -----------------------------------------------------------------------------
-- 4. 결정 기록: 도입 실험당 하나. 화면에서는 만들거나 바꾸지 않는다.
-- -----------------------------------------------------------------------------
create table public.eval_decisions (
  experiment_id   text primary key,
  -- 'adoption'으로 고정한 열을 복합 외래키에 넣어, 측정 실험에 결정을 다는 것을 DB가 거부한다.
  experiment_kind text not null default 'adoption' check (experiment_kind = 'adoption'),
  status          text not null check (status in ('adopted', 'not_adopted', 'deferred')),
  rationale       text not null check (length(rationale) > 0),
  decided_on      date not null,
  criteria_set_id text not null,
  -- 실험 종류를 바꾸려 하면 이 참조가 막는다. 결정이 남은 채 측정 실험으로 바뀌면 안 된다.
  foreign key (experiment_id, experiment_kind)
    references public.eval_experiments (id, kind) on update restrict on delete cascade,
  foreign key (experiment_id, criteria_set_id)
    references public.eval_experiments (id, criteria_set_id) on update restrict on delete cascade
);

-- -----------------------------------------------------------------------------
-- 5. 접근: service_role 전용
-- -----------------------------------------------------------------------------
alter table public.eval_policies enable row level security;
alter table public.eval_criteria_sets enable row level security;
alter table public.eval_experiments enable row level security;
alter table public.eval_decisions enable row level security;

-- RLS만으로도 0행이지만, 나중에 누가 정책을 추가해도 권한이 없으면 열리지 않게 권한도 회수한다.
revoke all on table public.eval_policies, public.eval_criteria_sets,
  public.eval_experiments, public.eval_decisions
  from anon, authenticated;

-- 이 프로젝트는 기본 권한을 열어 두지 않는다(0007 참고). 부여하지 않으면 등록 스크립트도 42501로 막힌다.
grant select, insert, update, delete on table public.eval_policies, public.eval_criteria_sets,
  public.eval_experiments, public.eval_decisions
  to service_role;

commit;

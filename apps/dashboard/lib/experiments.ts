import snapshot from "@/content/experiments.json";

/**
 * 커밋된 실험 스냅샷(scripts/eval_experiments.py export)을 읽는다.
 * 정본은 DB이고, 공개 화면은 렌더링 중 DB를 부르지 않는다.
 */
export type CriteriaCondition = {
  key: string;
  label: string;
  limit: string;
  actual: string;
  met: boolean;
};
export type CriteriaSet = {
  id: string;
  name: string;
  source_path: string;
  /** 출처 커밋을 찾지 못하면 null이다. 그때 사전 등록 여부도 null(확인 불가)이다. */
  source_commit: string | null;
  source_first_commit_at: string | null;
  earliest_run_at: string;
  preregistered: boolean | null;
  conditions: CriteriaCondition[];
  adopted: boolean;
};
export type AdoptionPolicy = {
  version: string;
  regression_rule: "per_question";
  require_improvement: boolean;
  max_excluded: number;
  max_cost_increase_pct: number;
  max_p95_increase_ms: number;
  limitation: string;
  defined_on: string;
};
export type Decision = {
  experiment_id: string;
  status: "adopted" | "not_adopted" | "deferred";
  rationale: string;
  decided_on: string;
  criteria_set_id: string;
};
export type ExperimentKind = "adoption" | "stability" | "grader";
export type Experiment = {
  id: string;
  kind: ExperimentKind;
  title: string;
  question: string;
  run_source: "research" | "reliability" | "local";
  baseline_run_id: string;
  candidate_run_id: string;
  baseline_role: string;
  candidate_role: string;
  criteria_set_id: string | null;
  policy_version: string | null;
  /** 판정 근거가 되는 다른 계약 경로. 채점 검증은 PR 관문 스펙을 가리킨다. */
  reference?: string | null;
  criteria?: CriteriaSet;
  policy?: AdoptionPolicy;
  decision?: Decision;
};

/**
 * 로컬 재채점 이력의 실험 정의. 비공개라 스냅샷에 없으므로 개발 화면이 이 값을 쓴다.
 * scripts/eval_experiments.py의 등록 값과 같아야 한다(테스트가 대조한다).
 */
export const localGraderExperiment = {
  id: "local-grader-check",
  kind: "grader",
  title: "채점 규칙 변경 확인",
  question: "새 검증은 기준선과 무엇이 달라졌나요?",
  run_source: "local",
  baseline_role: "지정한 기준 기록",
  candidate_role: "새 검증",
  criteria_set_id: null,
  policy_version: null,
  reference: "openspec/specs/offline-eval-regression-gate/spec.md",
} as const;

export const decisionLabels: Record<Decision["status"], string> = {
  adopted: "채택",
  not_adopted: "미채택",
  deferred: "판단 보류",
};

export type Snapshot = {
  /** 합성 데이터로 만든 기록이면 true. 공개 화면은 이 값으로만 합성 표기를 붙인다. */
  synthetic?: boolean;
  policies: AdoptionPolicy[];
  criteria_sets: CriteriaSet[];
  experiments: Omit<Experiment, "criteria" | "policy" | "decision">[];
  decisions: Decision[];
};

export const experimentSnapshot = snapshot as unknown as Snapshot;

/** 실행 출처로 실험을 찾고 기준·정책·결정을 붙인다. 참조가 끊긴 실험은 판정 없이 보이면 안 되므로 버린다. */
export function experimentFor(
  source: Experiment["run_source"],
  data: Snapshot = experimentSnapshot,
): Experiment | undefined {
  const base = data.experiments.find((item) => item.run_source === source);
  if (!base) return undefined;
  const criteria = data.criteria_sets.find(
    (item) => item.id === base.criteria_set_id,
  );
  const policy = data.policies.find(
    (item) => item.version === base.policy_version,
  );
  if (base.kind === "adoption" && (!criteria || !policy)) return undefined;
  return {
    ...base,
    criteria,
    policy,
    decision: data.decisions.find((item) => item.experiment_id === base.id),
  };
}

/**
 * 공개 랜딩에 보일 대표 실험: 결정 기록이 있는 첫 도입 실험.
 * 기준·정책·결정 중 하나라도 없으면 없음으로 돌려준다 — 랜딩이 판정을 지어내지 않게 한다.
 */
export type FeaturedAdoption = Experiment & {
  criteria: CriteriaSet;
  policy: AdoptionPolicy;
  decision: Decision;
};

export function featuredAdoption(
  data: Snapshot = experimentSnapshot,
): FeaturedAdoption | undefined {
  const base = data.experiments.find(
    (item) =>
      item.kind === "adoption" &&
      data.decisions.some((decision) => decision.experiment_id === item.id),
  );
  if (!base) return undefined;
  // experimentFor는 실행 출처로 찾으므로, 같은 출처의 실험이 둘이면 다른 실험을 돌려준다. 여기서는 id로 붙인다.
  const criteria = data.criteria_sets.find(
    (item) => item.id === base.criteria_set_id,
  );
  const policy = data.policies.find(
    (item) => item.version === base.policy_version,
  );
  const decision = data.decisions.find(
    (item) => item.experiment_id === base.id,
  );
  if (!criteria || !policy || !decision) return undefined;
  return { ...base, criteria, policy, decision };
}

/** 화면 전체가 같은 시간대로 보이게 한다. 정적 빌드와 브라우저 시간대가 다르면 하이드레이션이 어긋난다. */
export function kst(iso: string) {
  return new Date(iso).toLocaleString("ko-KR", {
    timeZone: "Asia/Seoul",
    month: "numeric",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

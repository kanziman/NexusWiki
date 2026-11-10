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
  source_commit: string;
  source_first_commit_at: string;
  earliest_run_at: string;
  preregistered: boolean;
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
  criteria?: CriteriaSet;
  policy?: AdoptionPolicy;
  decision?: Decision;
};

export const decisionLabels: Record<Decision["status"], string> = {
  adopted: "채택",
  not_adopted: "미채택",
  deferred: "판단 보류",
};

type Snapshot = {
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

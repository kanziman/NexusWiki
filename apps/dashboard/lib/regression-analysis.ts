import type { Experiment } from "./experiments";

/** 같은 평가 세트 안에서 문항을 맞춰 개선·회귀를 계산한다. 합계가 같아도 개별 회귀는 남긴다. */
export type AnalysisRow = {
  id: string;
  query: string;
  passed: boolean;
  reason: string | null;
  cost: number | null;
  latency: number | null;
  answer: string | null;
  failed: boolean;
  kind: string;
  expected?: string;
  /** 재검색 ON 실행에만 있다. 실제로 다시 검색했는지 모르면 결과 차이를 재검색 탓으로 오해한다. */
  research?: { status: string | null; calls: number };
};
export type AnalysisRun = {
  mode?: string;
  id: string;
  label: string;
  path: string;
  model: string;
  revision: string | null;
  /** 실행 시각(ISO). 같은 이름의 실행을 구분하는 고유값으로 함께 보여 준다. */
  createdAt?: string | null;
  conditions: Record<string, string>;
  rows: AnalysisRow[];
  cost: number;
  tokens: number;
  p50: number | null;
  p95: number | null;
};
export type AnalysisSuite = {
  guide?: {
    short: string;
    question: string;
    data: string;
    method: string;
    interpretation: string;
  };
  baselineId?: string;
  candidateId?: string;
  /** 이 세트에서 기준선과 후보가 각각 무엇인지. 없으면 일반 용어만 쓴다. */
  roles?: { baseline: string; candidate: string };
  /** 실험 기록. 도입 실험이면 공식 판정은 이 기록의 기준 세트가 정한다. */
  experiment?: Experiment;
  id: string;
  name: string;
  description: string;
  limitation: string;
  runs: AnalysisRun[];
};
export type Outcome =
  "regressed" | "improved" | "failed" | "passed" | "excluded";
export type ComparedRow = {
  id: string;
  query: string;
  before?: AnalysisRow;
  after?: AnalysisRow;
  outcome: Outcome;
};
export const outcomeLabels: Record<Outcome, string> = {
  regressed: "새로 실패",
  improved: "새로 통과",
  failed: "여전히 실패",
  passed: "계속 통과",
  excluded: "검사 중단",
};

export function researchLabel(research: NonNullable<AnalysisRow["research"]>) {
  if (research.calls > 0) return `재검색 ${research.calls}회 실행`;
  if (research.status === "sufficient")
    return "재검색 실행 안 됨 · 처음 찾은 근거로 충분하다고 판단";
  if (research.status === "decision_or_search_failed")
    return "재검색 실행 안 됨 · 판단이나 검색이 실패해 처음 근거로 답변";
  return `재검색 실행 안 됨 · 상태 ${research.status ?? "미기록"}`;
}

export function compareRuns(before: AnalysisRun, after: AnalysisRun) {
  const problems: string[] = [];
  if (before.id === after.id) problems.push("같은 실행은 비교할 수 없습니다.");
  const keys = new Set([
    ...Object.keys(before.conditions),
    ...Object.keys(after.conditions),
  ]);
  for (const key of keys)
    if (
      !before.conditions[key] ||
      before.conditions[key] !== after.conditions[key]
    )
      problems.push(`고정 조건 불일치: ${key}`);
  if (keys.size === 0) problems.push("고정 조건 기록이 없습니다.");
  const left = new Map(before.rows.map((row) => [row.id, row]));
  const right = new Map(after.rows.map((row) => [row.id, row]));
  if (!left.size || !right.size) problems.push("평가 문항이 없습니다.");
  if (left.size !== before.rows.length || right.size !== after.rows.length)
    problems.push("중복 문항 ID가 있습니다.");
  if (left.size !== right.size || [...left.keys()].some((id) => !right.has(id)))
    problems.push("문항 집합이 일치하지 않습니다.");
  const rows: ComparedRow[] = [
    ...new Set([...left.keys(), ...right.keys()]),
  ].map((id) => {
    const a = left.get(id),
      b = right.get(id);
    if (a && b && a.query !== b.query)
      problems.push(`질문이 바뀌었습니다: ${id}`);
    const outcome: Outcome =
      !a || !b || a.failed || b.failed
        ? "excluded"
        : a.passed && !b.passed
          ? "regressed"
          : !a.passed && b.passed
            ? "improved"
            : b.passed
              ? "passed"
              : "failed";
    return {
      id,
      query: b?.query ?? a?.query ?? id,
      before: a,
      after: b,
      outcome,
    };
  });
  const counts = {
    regressed: 0,
    improved: 0,
    failed: 0,
    passed: 0,
    excluded: 0,
  };
  for (const row of rows) counts[row.outcome]++;
  const eligible = rows.filter((row) => row.outcome !== "excluded");
  return {
    valid: problems.length === 0,
    problems,
    rows,
    counts,
    total: eligible.length,
    beforePassed: eligible.filter((row) => row.before?.passed).length,
    afterPassed: eligible.filter((row) => row.after?.passed).length,
    costChange: before.cost > 0 ? (after.cost / before.cost - 1) * 100 : null,
    p95Change:
      before.p95 !== null && after.p95 !== null ? after.p95 - before.p95 : null,
  };
}

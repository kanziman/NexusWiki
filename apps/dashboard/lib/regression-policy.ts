import type { AdoptionPolicy } from "./experiments";
import type { compareRuns } from "./regression-analysis";

type Analysis = ReturnType<typeof compareRuns>;

export type PolicyCondition = {
  key: "regression" | "excluded" | "improvement" | "cost" | "latency";
  label: string;
  actual: string;
  limit: string;
  met: boolean;
  /** 막는 조건으로 나열할 때 쓰는 실제 값 문구. 조건 이름(허용값)을 쓰면 "새로 실패 0개가 막는다"처럼 거꾸로 읽힌다. */
  finding: string;
};

export type PolicyVerdict =
  | { comparable: false; problems: string[] }
  | { comparable: true; adoptable: boolean; conditions: PolicyCondition[] };

const signed = (value: number, digits: number) =>
  `${value > 0 ? "+" : ""}${value.toFixed(digits)}`;

/**
 * 채택 정책으로 두 실행의 비교를 판정한다. 기준값은 정책 객체에서만 받는다.
 * 여기에 숫자를 하드코딩하면 정책 정본과 화면이 다시 어긋난다(design.md D6).
 */
export function evaluatePolicy(
  analysis: Analysis,
  policy: AdoptionPolicy,
): PolicyVerdict {
  if (!analysis.valid)
    return { comparable: false, problems: analysis.problems };
  const conditions: PolicyCondition[] = [
    {
      key: "regression",
      label: "새로 실패 0개 (질문 단위)",
      actual: `${analysis.counts.regressed}개`,
      limit: "0개",
      finding: `새로 실패 ${analysis.counts.regressed}개`,
      met: analysis.counts.regressed === 0,
    },
    {
      key: "excluded",
      label: `검사 중단 ${policy.max_excluded}개 이하`,
      actual: `${analysis.counts.excluded}개`,
      limit: `${policy.max_excluded}개`,
      finding: `검사 중단 ${analysis.counts.excluded}개`,
      // 검사를 마친 질문이 없으면 통과 수 비교가 의미 없으므로 충족으로 치지 않는다.
      met:
        analysis.total > 0 && analysis.counts.excluded <= policy.max_excluded,
    },
  ];
  if (policy.require_improvement)
    conditions.push({
      key: "improvement",
      label: "통과 수 증가",
      actual: `${analysis.beforePassed} → ${analysis.afterPassed}`,
      limit: "기준선보다 많음",
      finding: `통과 수 ${analysis.beforePassed} → ${analysis.afterPassed}`,
      met: analysis.afterPassed > analysis.beforePassed,
    });
  conditions.push(
    {
      key: "cost",
      label: `총비용 증가 ${policy.max_cost_increase_pct}% 이하`,
      actual:
        analysis.costChange === null
          ? "미측정"
          : `${signed(analysis.costChange, 1)}%`,
      limit: `+${policy.max_cost_increase_pct}%`,
      finding: `비용 ${analysis.costChange === null ? "미측정" : `${signed(analysis.costChange, 1)}%`}`,
      met:
        analysis.costChange !== null &&
        analysis.costChange <= policy.max_cost_increase_pct,
    },
    {
      key: "latency",
      label: `p95 응답 시간 증가 ${policy.max_p95_increase_ms / 1000}초 이하`,
      actual:
        analysis.p95Change === null
          ? "미측정"
          : `${signed(analysis.p95Change / 1000, 2)}초`,
      limit: `+${policy.max_p95_increase_ms / 1000}초`,
      finding: `p95 ${analysis.p95Change === null ? "미측정" : `${signed(analysis.p95Change / 1000, 2)}초`}`,
      met:
        analysis.p95Change !== null &&
        analysis.p95Change <= policy.max_p95_increase_ms,
    },
  );
  return {
    comparable: true,
    adoptable: conditions.every((condition) => condition.met),
    conditions,
  };
}

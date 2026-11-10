import { describe, expect, it } from "vitest";
import { experimentSnapshot, type AdoptionPolicy } from "@/lib/experiments";
import { compareRuns, type AnalysisRun } from "@/lib/regression-analysis";
import { evaluatePolicy } from "@/lib/regression-policy";
import { regressionSuites } from "@/lib/regression-data";

const v1 = experimentSnapshot.policies.find(
  (item) => item.version === "adoption-v1",
)!;

function run(id: string, passed: boolean[], cost: number, p95: number) {
  return {
    id,
    label: id,
    path: "HTTP",
    model: "m",
    revision: null,
    conditions: { corpus: "c" },
    rows: passed.map((ok, i) => ({
      id: `q${i}`,
      query: `q${i}`,
      passed: ok,
      reason: null,
      cost: null,
      latency: null,
      answer: null,
      failed: false,
      kind: "x",
    })),
    cost,
    tokens: 0,
    p50: null,
    p95,
  } satisfies AnalysisRun;
}

describe("채택 정책 평가", () => {
  it("재검색 실험은 정책 v1에서도 채택 불가이고 질문 단위 회귀가 막는다", () => {
    const research = regressionSuites.find((suite) => suite.id === "research")!;
    const [off, on] = research.runs;
    const verdict = evaluatePolicy(compareRuns(off, on), v1);
    expect(verdict.comparable).toBe(true);
    if (!verdict.comparable) return;
    expect(verdict.adoptable).toBe(false);
    expect(verdict.conditions.filter((c) => !c.met).map((c) => c.key)).toEqual([
      "regression",
      "improvement",
      "cost",
    ]);
  });

  it("회귀가 없고 비용 안이어도 통과 수가 같으면 채택 불가다", () => {
    const before = run("a", [true, false], 100, 1000);
    const after = run("b", [true, false], 120, 1500);
    const verdict = evaluatePolicy(compareRuns(before, after), v1);
    expect(verdict.comparable && verdict.adoptable).toBe(false);
    expect(
      verdict.comparable &&
        verdict.conditions.find((c) => c.key === "improvement")?.met,
    ).toBe(false);
  });

  it("한 질문의 회귀는 다른 질문의 개선이 가리지 못한다", () => {
    const before = run("a", [true, false, false], 100, 1000);
    const after = run("b", [false, true, true], 100, 1000);
    const verdict = evaluatePolicy(compareRuns(before, after), v1);
    expect(verdict.comparable && verdict.adoptable).toBe(false);
    expect(
      verdict.comparable &&
        verdict.conditions.find((c) => c.key === "regression")?.actual,
    ).toBe("1개");
  });

  it("기준값은 정책 객체에서만 온다", () => {
    // 정책 값을 바꾸면 판정이 따라 바뀌어야 한다. 화면이나 함수에 숫자가 남아 있으면 이 테스트가 깨진다.
    const before = run("a", [true, false], 100, 1000);
    const after = run("b", [true, true], 170, 30000);
    const strict = evaluatePolicy(compareRuns(before, after), v1);
    expect(strict.comparable && strict.adoptable).toBe(false);
    const loose: AdoptionPolicy = {
      ...v1,
      max_cost_increase_pct: 80,
      max_p95_increase_ms: 30000,
    };
    const relaxed = evaluatePolicy(compareRuns(before, after), loose);
    expect(relaxed.comparable && relaxed.adoptable).toBe(true);
    expect(
      relaxed.comparable &&
        relaxed.conditions.find((c) => c.key === "cost")?.label,
    ).toBe("총비용 증가 80% 이하");
  });

  it("조건이 다른 실행은 판정하지 않는다", () => {
    const before = run("a", [true], 100, 1000);
    const after = {
      ...run("b", [true], 100, 1000),
      conditions: { corpus: "d" },
    };
    const verdict = evaluatePolicy(compareRuns(before, after), v1);
    expect(verdict.comparable).toBe(false);
  });
});

import { describe, expect, it } from "vitest";
import { GET } from "@/app/showcase/regression/experiments.json/route";
import {
  experimentFor,
  experimentSnapshot,
  featuredAdoption,
  kst,
} from "@/lib/experiments";
import { regressionSuites } from "@/lib/regression-data";

describe("실험 스냅샷", () => {
  it("다운로드 JSON은 화면이 읽은 스냅샷과 같다", async () => {
    const response = GET();
    expect(response.headers.get("Content-Disposition")).toContain(
      "eval-experiments.v1.json",
    );
    expect(await response.json()).toEqual(experimentSnapshot);
  });

  it("재검색 세트는 실험 기록의 쌍과 기준·결정을 쓴다", () => {
    const research = regressionSuites.find((suite) => suite.id === "research")!;
    expect(research.experiment?.kind).toBe("adoption");
    expect([research.baselineId, research.candidateId]).toEqual(["off", "on"]);
    expect(research.experiment?.criteria?.preregistered).toBe(false);
    expect(research.experiment?.decision?.status).toBe("not_adopted");
    expect(research.experiment?.policy?.version).toBe("adoption-v1");
  });

  it("기준 세트 참조가 끊긴 도입 실험은 판정 없이 보이지 않는다", () => {
    const broken = structuredClone(experimentSnapshot);
    broken.criteria_sets = [];
    expect(experimentFor("research", broken)).toBeUndefined();
  });

  it("대표 실험은 결정 기록이 있는 도입 실험이고 참조가 끊기면 없다", () => {
    expect(featuredAdoption()?.id).toBe("ask-evidence-research");

    const noPolicy = structuredClone(experimentSnapshot);
    noPolicy.policies = [];
    expect(featuredAdoption(noPolicy)).toBeUndefined();

    const noDecision = structuredClone(experimentSnapshot);
    noDecision.decisions = [];
    expect(featuredAdoption(noDecision)).toBeUndefined();
  });

  it("같은 실행 출처의 실험이 앞에 있어도 결정이 있는 도입 실험을 고른다", () => {
    const crowded = structuredClone(experimentSnapshot);
    const research = crowded.experiments.find(
      (item) => item.id === "ask-evidence-research",
    )!;
    crowded.experiments.unshift({
      ...research,
      id: "research-draft",
      title: "결정 전 초안",
    });

    expect(featuredAdoption(crowded)?.id).toBe("ask-evidence-research");
  });

  it("시각은 브라우저 시간대와 관계없이 한국 시간으로 보인다", () => {
    expect(kst("2026-11-08T23:53:39+00:00")).toContain("08:53");
  });
});

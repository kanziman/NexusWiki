import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { PublicLandingEvaluation } from "@/components/public-landing/PublicLandingEvaluation";
import { experimentSnapshot, type Snapshot } from "@/lib/experiments";

function cloneSnapshot(): Snapshot {
  return structuredClone(experimentSnapshot);
}

function featuredBlock() {
  return screen.getByRole("article", { name: /재검색 도입/ });
}

describe("PublicLandingEvaluation", () => {
  it("대표 실험 판정을 스냅샷 값 그대로 합성 표기와 함께 보인다", () => {
    render(<PublicLandingEvaluation />);

    const block = featuredBlock();
    const criteria = experimentSnapshot.criteria_sets[0];
    const met = criteria.conditions.filter((item) => item.met).length;

    expect(block).toHaveTextContent("대표 실험 · 합성 시나리오 기준");
    expect(block).toHaveTextContent("미채택");
    expect(block).toHaveTextContent(
      `원래 기준 ${criteria.conditions.length}개 중 ${met}개 충족`,
    );
    expect(block).toHaveTextContent("원래 기준 6개 중 3개 충족");
    for (const item of criteria.conditions.filter((entry) => !entry.met)) {
      expect(block).toHaveTextContent(item.label);
      expect(block).toHaveTextContent(
        `실제 ${item.actual} · 허용 ${item.limit}`,
      );
    }
    expect(block).toHaveTextContent("실제 +66.4% · 허용 +50%");
    // 충족한 조건은 미충족 목록에 섞이지 않는다.
    expect(block).not.toHaveTextContent("위조 인용 증가 없음");
    expect(
      within(block).getByRole("link", { name: "실험 기록 자세히 보기" }),
    ).toHaveAttribute("href", "/showcase/evidence-research");
  });

  it("평가 페이지 카드 3개를 각 공개 페이지로 연결한다", () => {
    render(<PublicLandingEvaluation />);

    expect(screen.getByRole("link", { name: /평가 설계/ })).toHaveAttribute(
      "href",
      "/showcase/evaluation",
    );
    expect(
      screen.getByRole("link", { name: /통제 전후 비교/ }),
    ).toHaveAttribute("href", "/showcase/controlled-ai");
    expect(screen.getByRole("link", { name: /회귀 작업대/ })).toHaveAttribute(
      "href",
      "/showcase/regression",
    );
  });

  it("기준 세트 참조가 끊기면 판정·수치 없이 소개와 카드만 보인다", () => {
    const broken = cloneSnapshot();
    broken.criteria_sets = [];
    const { container } = render(<PublicLandingEvaluation snapshot={broken} />);

    expect(screen.queryByRole("article")).toBeNull();
    expect(container).not.toHaveTextContent("미채택");
    expect(container).not.toHaveTextContent("충족");
    expect(container).not.toHaveTextContent("+66.4%");
    expect(
      screen.getByRole("heading", {
        name: "AI의 답변을, 검증하며 개선합니다.",
      }),
    ).toBeInTheDocument();
    expect(screen.getAllByRole("link")).toHaveLength(3);
  });

  it("결정 기록이 없으면 대표 실험을 보이지 않는다", () => {
    const undecided = cloneSnapshot();
    undecided.decisions = [];
    render(<PublicLandingEvaluation snapshot={undecided} />);

    expect(screen.queryByRole("article")).toBeNull();
  });

  it("합성이 아닌 스냅샷에는 합성 표기를 붙이지 않는다", () => {
    const real = cloneSnapshot();
    real.synthetic = false;
    render(<PublicLandingEvaluation snapshot={real} />);

    expect(featuredBlock()).toHaveTextContent("대표 실험");
    expect(featuredBlock()).not.toHaveTextContent("합성 시나리오");
  });

  it("링크가 대상 라우트를 프리페치하지 않는다", () => {
    const source = readFileSync(
      resolve(
        process.cwd(),
        "components/public-landing/PublicLandingEvaluation.tsx",
      ),
      "utf8",
    );
    const links = source.match(/<Link\b[^>]*>/g) ?? [];

    expect(links.length).toBeGreaterThan(0);
    for (const link of links) {
      expect(link).toContain("prefetch={false}");
    }
  });
});

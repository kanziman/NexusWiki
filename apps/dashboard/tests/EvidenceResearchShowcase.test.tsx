import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import {
  EvidenceResearchShowcase,
  type ResearchEvaluation,
} from "@/components/EvidenceResearchShowcase";
import evaluation from "@/content/evidence-research.json";

const missing: ResearchEvaluation = {
  version: 1,
  synthetic: true,
  valid: false,
  adopted: false,
  checks: {},
  conditions: {},
  runs: [],
  summary: {},
  rows: [],
  measurement_failures: 0,
  recovery: { eligible: 0, evidence: 0, answer: 0, rate: null },
  method: "합성 평가 방법",
};

describe("재검색 실험 공개 페이지", () => {
  it("미측정 수치를 개선으로 표시하지 않는다", () => {
    render(<EvidenceResearchShowcase evaluation={missing} />);
    expect(screen.getByRole("note")).toHaveTextContent("합성 평가");
    expect(
      screen.getByRole("heading", { name: "아직 유효한 비교가 없습니다" }),
    ).toBeInTheDocument();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: /JSON 다운로드/ })).toHaveAttribute(
      "href",
      "/showcase/evidence-research/results.json",
    );
  });

  it("복구 필터와 문항의 위험한 문자열을 텍스트로 표시한다", () => {
    const row = {
      id: "r01",
      pair: 1,
      query: "<script>bad()</script>",
      type: "comparison",
      before_pass: false,
      after_pass: true,
      before_reason: "인용 부족",
      after_reason: null,
      eligible: true,
      evidence_recovered: true,
      answer_recovered: true,
      measurement_failed: false,
      initial_all_found: false,
      final_all_found: true,
      before_ms: 1000,
      after_ms: 2000,
      before_cost: 10,
      after_cost: 20,
      tool_calls: 1,
      research_status: "searched",
    };
    const { container } = render(
      <EvidenceResearchShowcase evaluation={{ ...missing, rows: [row] }} />,
    );
    expect(screen.getByText(row.query)).toBeInTheDocument();
    expect(container.querySelector("script")).toBeNull();
    fireEvent.change(screen.getByLabelText("문항 보기"), {
      target: { value: "regressed" },
    });
    expect(screen.queryByText(row.query)).not.toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("문항 보기"), {
      target: { value: "recovered" },
    });
    expect(screen.getByText(row.query)).toBeInTheDocument();
  });

  it("유효한 실제 공개 기록의 쌍 수와 분모를 기록에서 센다", () => {
    const published = evaluation as unknown as ResearchEvaluation;
    const pairs = new Set(published.rows.map((row) => row.pair)).size;
    const regression = published.rows.filter(
      (row) => row.type === "regression",
    ).length;
    render(<EvidenceResearchShowcase evaluation={published} />);
    expect(published.valid).toBe(true);
    expect(
      screen.getByRole("heading", {
        name: "채택 기준 미달 · 기본 설정 OFF 유지",
      }),
    ).toBeInTheDocument();
    const table = screen.getByRole("table");
    expect(table).toHaveTextContent(
      `${published.rows.length / pairs}문항 ${pairs}쌍`,
    );
    const regressionRow = within(table)
      .getByRole("rowheader", { name: "기존 문항 통과" })
      .closest("tr") as HTMLElement;
    const [offCell, onCell] = within(regressionRow).getAllByRole("cell");
    expect(offCell).toHaveTextContent(
      `${published.summary.off?.regression_passed} / ${regression}`,
    );
    expect(onCell).toHaveTextContent(
      `${published.summary.on?.regression_passed} / ${regression}`,
    );
    expect(table).not.toHaveTextContent("3회");
    expect(screen.getByText(/복구율은 미측정/)).toBeInTheDocument();
    const pairSelect = screen.getByLabelText("실행 쌍");
    expect(pairSelect.querySelectorAll("option")).toHaveLength(pairs);
    expect(screen.getByRole("status")).toHaveTextContent(
      `${published.rows.length / pairs}문항`,
    );
  });

  it("무효 기록에서는 행별 복구 표시를 하지 않는다", () => {
    const row = {
      id: "r02",
      pair: 1,
      query: "무효 기록의 문항",
      type: "comparison",
      before_pass: false,
      after_pass: true,
      before_reason: "인용 부족",
      after_reason: null,
      eligible: true,
      evidence_recovered: true,
      answer_recovered: true,
      measurement_failed: false,
      initial_all_found: false,
      final_all_found: true,
      before_ms: 1000,
      after_ms: 2000,
      before_cost: 10,
      after_cost: 20,
      tool_calls: 1,
      research_status: "searched",
    };
    render(
      <EvidenceResearchShowcase evaluation={{ ...missing, rows: [row] }} />,
    );
    expect(screen.getByText(row.query)).toBeInTheDocument();
    expect(screen.queryByText(/· 복구/)).not.toBeInTheDocument();
  });

  it("공개 경계에서 운영 데이터 클라이언트를 사용하지 않는다", () => {
    for (const path of [
      "app/showcase/evidence-research/page.tsx",
      "app/showcase/evidence-research/results.json/route.ts",
      "components/EvidenceResearchShowcase.tsx",
    ]) {
      const source = readFileSync(resolve(process.cwd(), path), "utf8");
      expect(source).not.toMatch(
        /from ["'].*(?:supabase|api-client|server-client)/,
      );
      expect(source).not.toMatch(/\bfetch\s*\(/);
    }
  });
});

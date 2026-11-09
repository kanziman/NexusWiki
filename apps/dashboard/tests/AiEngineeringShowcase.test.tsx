import { render, screen, fireEvent, within } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import EvaluationPage from "@/app/showcase/evaluation/page";
import ControlledPage from "@/app/showcase/controlled-ai/page";
import ResearchPage from "@/app/showcase/evidence-research/page";
import { AiEngineeringShowcase } from "@/components/AiEngineeringShowcase";
import type { EvaluationRecord } from "@/components/EvaluationShowcase";
import type { ControlledAiEvidence } from "@/components/ControlledAiShowcase";
import type { ResearchEvaluation } from "@/components/EvidenceResearchShowcase";
import record from "@/content/evaluation.json";
import controlled from "@/content/controlled-ai/step1.json";
import research from "@/content/evidence-research.json";

vi.mock("next/navigation", () => ({ redirect: vi.fn() }));
import { redirect } from "next/navigation";

describe("통합 AI 엔지니어링 사례", () => {
  it("한 화면에서 세 사례와 근거 유형을 구분하고 상세를 같은 자리에서 펼친다", () => {
    render(<EvaluationPage />);
    expect(screen.getAllByRole("main")).toHaveLength(1);
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    for (const id of ["evaluate", "control", "research"])
      expect(document.getElementById(id)).not.toBeNull();
    expect(
      screen.getByText(/가짜 공급자를 사용한 자동화 테스트/),
    ).toBeInTheDocument();
    const summary = screen.getByText("통제 사례 전체 펼치기");
    fireEvent.click(summary);
    expect(summary.closest("details")).toHaveAttribute("open");
    expect(
      within(summary.closest("details")!).getByText("compile_retry_cost"),
    ).toBeInTheDocument();
    expect(document.querySelector('a[target="_blank"]')).toBeNull();
    expect(
      screen.getByRole("link", { name: "반복 측정의 질문별 결과 살펴보기" }),
    ).toHaveAttribute("href", "/showcase/regression#reliability");
    expect(
      screen.getByRole("link", { name: "재검색 실험의 질문별 결과 살펴보기" }),
    ).toHaveAttribute("href", "/showcase/regression#research");
    expect(
      screen.getByRole("table", { name: "재검색 OFF ON 핵심 비교" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "재검색 ON" }),
    ).toBeInTheDocument();
    const links = screen.getAllByRole("link");
    expect(links.some((link) => link.getAttribute("href") === "#control")).toBe(
      true,
    );
    expect(
      links.some(
        (link) => link.getAttribute("href") === "/showcase/controlled-ai",
      ),
    ).toBe(false);
    expect(
      screen.getByText(/첫 검색에서 기대 문서가 빠진 복구 대상은 0개/),
    ).toBeInTheDocument();
  });
  it("무효 비교에서 수치 요약과 채택 판정을 보류한다", () => {
    render(
      <AiEngineeringShowcase
        record={record as unknown as EvaluationRecord}
        controlled={controlled as ControlledAiEvidence}
        research={
          { ...research, valid: false } as unknown as ResearchEvaluation
        }
      />,
    );
    expect(
      screen.getByText(/유효하고 조건이 일치하는 비교 기록이 없어/),
    ).toBeInTheDocument();
    expect(screen.queryByText("평가 전체 비용")).not.toBeInTheDocument();
  });
  it("이전 주소는 통합 페이지의 해당 구역으로 연결한다", () => {
    ControlledPage();
    expect(redirect).toHaveBeenCalledWith("/showcase/evaluation#control");
    ResearchPage();
    expect(redirect).toHaveBeenCalledWith("/showcase/evaluation#research");
  });
});

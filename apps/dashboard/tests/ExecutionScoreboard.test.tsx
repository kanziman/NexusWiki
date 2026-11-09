import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import {
  ExecutionScoreboard,
  type ExecutionRecords,
} from "@/components/ExecutionScoreboard";
import committed from "@/content/evaluation-runs.json";
import evaluation from "@/content/evaluation.json";
import { GET } from "@/app/showcase/evaluation/runs.json/route";

describe("공개 실행 성적표", () => {
  it("세 회차를 선택하고 실패·전체·거절 문항을 필터링한다", () => {
    render(<ExecutionScoreboard />);
    const table = screen.getByRole("table");
    expect(within(table).getAllByRole("button")).toHaveLength(3);
    expect(
      screen.getByText("입고 검수는 도착 후 얼마 안에 끝내야 하나요?"),
    ).toBeInTheDocument();
    expect(
      screen.queryByText("당일배송 주문 마감 시간은 언제인가요?"),
    ).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /HTTP 2/ }));
    expect(screen.getByRole("button", { name: /HTTP 2/ })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(
      screen.getByRole("heading", { name: "HTTP 2의 문항 기록" }),
    ).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "전체 30" }));
    expect(
      screen.getByText("당일배송 주문 마감 시간은 언제인가요?"),
    ).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "거절 1" }));
    expect(
      screen.getByText("푸른나래로지스의 작년 영업이익은 얼마인가요?"),
    ).toBeInTheDocument();
    expect(
      screen.queryByText("입고 검수는 도착 후 얼마 안에 끝내야 하나요?"),
    ).not.toBeInTheDocument();
  });
  it("실패 문항에서 기대 표현·실제 답변·판정 근거를 대조한다", () => {
    render(<ExecutionScoreboard />);
    fireEvent.click(
      screen.getByText("입고 검수는 도착 후 얼마 안에 끝내야 하나요?"),
    );
    const pre = screen.getByLabelText("q06 실제 답변");
    expect(pre.textContent).toBe(
      committed.runs[0].rows.find((r) => r.id === "q06")!.response_text,
    );
    expect(screen.getByText("2시간")).toBeInTheDocument();
    expect(screen.getByText("기대 표현을 찾지 못함")).toBeInTheDocument();
    expect(screen.getByText("위키 1개 · 원문 1개")).toBeInTheDocument();
    expect(pre.closest("details")).toHaveAttribute("open");
  });
  it("스크립트 모양의 본문도 실행 가능한 HTML로 취급하지 않는다", () => {
    const data = structuredClone(committed) as ExecutionRecords;
    data.runs[0].rows[5].response_text = '<script>alert("x")</script>';
    render(<ExecutionScoreboard records={data} />);
    expect(screen.getByLabelText("q06 실제 답변").textContent).toBe(
      '<script>alert("x")</script>',
    );
    expect(document.querySelector("script")).toBeNull();
  });
  it("무효·빈 기록은 성적표를 만들지 않는다", () => {
    const { rerender } = render(<ExecutionScoreboard available={false} />);
    expect(screen.queryByRole("table")).toBeNull();
    rerender(
      <ExecutionScoreboard
        records={{
          schema: "synthetic-execution-records-v1",
          synthetic: true,
          runs: [],
        }}
      />,
    );
    expect(screen.getByRole("status")).toHaveTextContent("기록이 없어");
  });
  it("공개 집계와 90개 문항이 일치하고 다운로드도 같은 기록이다", async () => {
    for (const [i, run] of committed.runs.entries()) {
      expect(run.rows).toHaveLength(30);
      expect(
        run.rows.filter((r) => r.passed && r.kind === "answerable"),
      ).toHaveLength(evaluation.series.runs[i].answerable_passed);
      expect(run.rows.reduce((sum, r) => sum + (r.cost_micros ?? 0), 0)).toBe(
        run.cost_micros,
      );
    }
    expect(await GET().json()).toEqual(committed);
  });
});

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { RegressionDashboard } from "@/components/RegressionDashboard";
import { compareRuns } from "@/lib/regression-analysis";
import { regressionSuites } from "@/lib/regression-data";

beforeEach(() => {
  const storage = new Map<string, string>();
  vi.stubGlobal("localStorage", {
    getItem: (key: string) => storage.get(key) ?? null,
    setItem: (key: string, value: string) => storage.set(key, value),
    removeItem: (key: string) => storage.delete(key),
  });
});
afterEach(() => vi.unstubAllGlobals());

describe("회귀 분석 계산", () => {
  it("전체 통과 수가 같아도 개선과 회귀를 별도로 계산한다", () => {
    const [a, b] = regressionSuites[0].runs;
    const result = compareRuns(a, b);
    expect(result.valid).toBe(true);
    expect([result.beforePassed, result.afterPassed]).toEqual([39, 39]);
    expect(result.counts.regressed).toBe(1);
    expect(result.counts.improved).toBe(1);
    expect(result.rows.find((row) => row.id === "q04")?.outcome).toBe(
      "regressed",
    );
    expect(result.costChange).toBeCloseTo(66.4266, 2);
    expect(
      compareRuns(b, a).rows.find((row) => row.id === "q04")?.outcome,
    ).toBe("improved");
  });
  it("중복·누락·조건 불일치·동일 실행을 막고 장애는 회귀로 세지 않는다", () => {
    const [a, b] = structuredClone(regressionSuites[0].runs);
    expect(compareRuns(a, a).valid).toBe(false);
    expect(
      compareRuns(a, { ...b, conditions: { ...b.conditions, model: "other" } })
        .valid,
    ).toBe(false);
    expect(compareRuns(a, { ...b, rows: b.rows.slice(1) }).valid).toBe(false);
    expect(compareRuns(a, { ...b, rows: [...b.rows, b.rows[0]] }).valid).toBe(
      false,
    );
    b.rows.find((row) => row.id === "q04")!.failed = true;
    const result = compareRuns(a, b);
    expect(result.counts.excluded).toBe(1);
    expect(result.counts.regressed).toBe(0);
    expect(result.total).toBe(41);
  });
});

describe("회귀 분석 작업대", () => {
  it("실험 링크의 주제를 선택하고 해당 설계로 돌아간다", () => {
    window.history.replaceState(null, "", "#reliability");
    const { unmount } = render(<RegressionDashboard />);
    expect(screen.getByLabelText("기준 실행")).toHaveValue("run-1");
    expect(
      screen.getByRole("link", { name: "평가 설계와 실험으로 돌아가기" }),
    ).toHaveAttribute("href", "/showcase/evaluation#evaluate");
    fireEvent.click(
      screen.getByRole("button", { name: /재검색의 효과와 비용/ }),
    );
    expect(
      screen.getByRole("link", { name: "평가 설계와 실험으로 돌아가기" }),
    ).toHaveAttribute("href", "/showcase/evaluation#research");
    unmount();
    window.history.replaceState(null, "", window.location.pathname);
  });
  it("결과를 먼저 보여주고 로컬 기록이 도착해도 주제를 바꾸지 않는다", async () => {
    const runs = structuredClone(regressionSuites[1].runs.slice(0, 2)).map(
      (run) => ({ ...run, mode: "rescore" }),
    );
    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation(() =>
        Promise.resolve(
          Response.json({
            runs,
            jobs: [],
            baseline_id: runs[0].id,
            model_ready: false,
          }),
        ),
      ),
    );
    render(<RegressionDashboard localEnabled />);
    const heading = screen.getByRole("heading", { level: 1 });
    expect(heading).toHaveTextContent(regressionSuites[0].guide!.question);
    expect(
      screen.getByText("42개 중 39개가 검사 기준을 통과했습니다."),
    ).toBeInTheDocument();
    expect(
      screen.getByText("비교할 검사 기록과 상세 수치 보기").closest("details"),
    ).not.toHaveAttribute("open");
    await screen.findByRole("button", { name: "내 검사 결과 보기" });
    expect(heading).toHaveTextContent(regressionSuites[0].guide!.question);
    fireEvent.click(screen.getByRole("button", { name: "내 검사 결과 보기" }));
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(
      "이번 검증은 기준 실행과 무엇이 달라졌나요?",
    );
    expect(screen.getByText(/추가 모델 호출 비용/)).toHaveTextContent(/없/);
  });
  it("회귀부터 선택하고 검색·필터·실행 맞바꾸기가 동작한다", () => {
    render(<RegressionDashboard />);
    expect(
      screen.getByRole("region", { name: "q04 문항 상세" }),
    ).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "새로 통과 1" }));
    expect(
      screen.getByRole("region", { name: "q03 문항 상세" }),
    ).toBeInTheDocument();
    fireEvent.change(screen.getByRole("textbox", { name: "문항 검색" }), {
      target: { value: "no-match" },
    });
    expect(screen.getByText("해당하는 질문이 없습니다")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "전체 문항 보기" }));
    expect(screen.getByRole("status")).toHaveTextContent("42문항 표시");
    fireEvent.click(
      screen.getByRole("button", { name: "기준과 비교 실행 맞바꾸기" }),
    );
    expect(screen.getByLabelText("기준 실행")).toHaveValue("on");
    expect(screen.getByLabelText("비교 실행")).toHaveValue("off");
    expect(
      screen.getByRole("region", { name: "q03 문항 상세" }),
    ).toBeInTheDocument();
  });
  it("반복 측정은 별도 세트로 고르고 실제 답변을 나란히 본다", () => {
    render(<RegressionDashboard />);
    fireEvent.click(screen.getByRole("button", { name: /Ask 반복 측정/ }));
    expect(screen.getByLabelText("기준 실행")).toHaveValue("run-1");
    expect(screen.getByLabelText("q06 기준 실행 답변")).toHaveTextContent(
      "48시간",
    );
    expect(screen.getByLabelText("q06 비교 실행 답변")).toHaveTextContent(
      "48시간",
    );
    expect(screen.getByText("기대 표현 / 2시간")).toBeInTheDocument();
  });
  it("같은 실행 선택 시 지표·검토 메모를 숨기고 내보내기를 막는다", () => {
    render(<RegressionDashboard />);
    fireEvent.change(screen.getByLabelText("비교 실행"), {
      target: { value: "off" },
    });
    expect(screen.getByRole("alert")).toHaveTextContent("같은 실행");
    expect(
      screen.queryByRole("region", { name: "비교 결과 요약" }),
    ).not.toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "비교 결과 JSON" }),
    ).toBeDisabled();
    expect(
      screen.queryByRole("textbox", { name: "판단 근거" }),
    ).not.toBeInTheDocument();
  });
  it("메모를 브라우저에 저장·복원하고 다른 비교와 분리한다", async () => {
    const { unmount } = render(<RegressionDashboard />);
    fireEvent.click(screen.getByRole("button", { name: "메모 저장" }));
    expect(screen.getByRole("alert")).toHaveTextContent("판단의 근거");
    fireEvent.change(screen.getByLabelText("허용 비용 증가 (%)"), {
      target: { value: "70" },
    });
    fireEvent.change(screen.getByLabelText("검토 의견"), {
      target: { value: "hold" },
    });
    fireEvent.change(screen.getByRole("textbox", { name: "판단 근거" }), {
      target: { value: "q04 회귀와 비용 증가로 보류" },
    });
    fireEvent.click(screen.getByRole("button", { name: "메모 저장" }));
    expect(
      screen.getByText("이 브라우저에 검토 메모를 저장했습니다."),
    ).toBeInTheDocument();
    unmount();
    render(<RegressionDashboard />);
    await waitFor(() =>
      expect(screen.getByLabelText("허용 비용 증가 (%)")).toHaveValue(70),
    );
    await waitFor(() =>
      expect(screen.getByRole("textbox", { name: "판단 근거" })).toHaveValue(
        "q04 회귀와 비용 증가로 보류",
      ),
    );
    fireEvent.click(
      screen.getByRole("button", { name: "기준과 비교 실행 맞바꾸기" }),
    );
    expect(screen.getByRole("textbox", { name: "판단 근거" })).toHaveValue("");
  });
  it("저장 실패를 성공으로 표시하지 않고 빈 데이터도 설명한다", () => {
    vi.stubGlobal("localStorage", {
      getItem: () => null,
      setItem: () => {
        throw new Error("quota");
      },
    });
    const { unmount } = render(<RegressionDashboard />);
    fireEvent.change(screen.getByRole("textbox", { name: "판단 근거" }), {
      target: { value: "검토 필요" },
    });
    fireEvent.click(screen.getByRole("button", { name: "메모 저장" }));
    expect(screen.getByRole("alert")).toHaveTextContent("저장하지 못했습니다");
    unmount();
    render(<RegressionDashboard suites={[]} />);
    expect(
      screen.getByRole("heading", { name: "평가 실행을 준비해 주세요" }),
    ).toBeInTheDocument();
  });
});

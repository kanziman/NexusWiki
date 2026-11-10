import { fireEvent, render, screen, within } from "@testing-library/react";
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
    expect(screen.getByLabelText("기준선")).toHaveValue("run-1");
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
    // 재검색은 도입 실험이라 원래 기준(D4)의 저장 판정이 공식 판정이다. 화면이 다시 계산하지 않는다.
    expect(screen.getByText("원래 기준 미충족")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "원래 기준 6개 중 3개 미충족" }),
    ).toBeInTheDocument();
    // 이름만으로는 실행을 짚을 수 없다. id·리비전·역할이 함께 보여야 한다.
    const compared = within(screen.getByLabelText("비교한 실행"));
    expect(compared.getByText("도입 검토안")).toBeInTheDocument();
    expect(compared.getByText("현재 방식")).toBeInTheDocument();
    expect(compared.getByText(/^on · 5dded7b\+dirty · /)).toBeInTheDocument();
    expect(compared.getByText(/^off · 5dded7b\+dirty · /)).toBeInTheDocument();
    const gates = within(screen.getByRole("list", { name: "적용 조건" }));
    expect(gates.getAllByLabelText("미충족")).toHaveLength(3);
    expect(gates.getAllByLabelText("충족")).toHaveLength(3);
    for (const label of [
      "답변 복구 1건 이상",
      "전체 통과 수 증가",
      "총비용 증가 50% 이하",
    ])
      expect(
        gates.getByText(label).closest("li")!.querySelector("[aria-label]"),
      ).toHaveAttribute("aria-label", "미충족");
    expect(gates.getByText("+66.4% · 허용 +50%")).toBeInTheDocument();
    // 기준 출처가 실행보다 늦게 커밋됐으므로 사전 등록이라고 말하면 안 된다.
    const provenance = within(screen.getByLabelText("판정 기준과 결정"));
    expect(
      provenance.getByText("실행보다 먼저 기록됐음을 증명하지 못함"),
    ).toBeInTheDocument();
    expect(provenance.getByText("0f9bbbe")).toBeInTheDocument();
    expect(provenance.queryByText(/사전 등록 ·/)).not.toBeInTheDocument();
    expect(provenance.getByText("미채택")).toBeInTheDocument();
    // 공식 판정 쌍은 고정이다. 맞바꾸기와 기준 입력이 있으면 판정과 목록이 다른 쌍을 말한다.
    expect(
      screen.queryByRole("button", { name: "기준선과 후보 맞바꾸기" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByLabelText("허용 비용 증가 (%)"),
    ).not.toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "실험 기록 JSON" }),
    ).toHaveAttribute("href", "/showcase/regression/experiments.json");
    expect(screen.getByText(/통과 39\/42 → 39\/42/)).toBeInTheDocument();
    expect(
      screen.getByText("실행 고르기와 기준 설정").closest("details"),
    ).not.toHaveAttribute("open");
    // 판정 다음에는 실패한 질문이 와야 한다. 설정 섹션이 사이에 끼면 다시 건너뛰기 버튼이 필요해진다.
    const questions = screen.getByRole("heading", { name: /질문별 결과/ });
    const settings = screen.getByText("실행 고르기와 기준 설정");
    expect(
      questions.compareDocumentPosition(settings) &
        Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
    expect(gates.getByText("채점 방식")).toBeInTheDocument();
    expect(gates.getAllByLabelText("참고")).toHaveLength(1);
    // 다른 실험 화면에는 실행 서랍과 로컬 기록 안내가 없다.
    expect(screen.queryByText("내 검증 실행하기")).not.toBeInTheDocument();
    expect(screen.queryByText(/이 컴퓨터에 저장된/)).not.toBeInTheDocument();
    const tools = within(screen.getByRole("group", { name: "로컬 개발 도구" }));
    fireEvent.click(tools.getByRole("button", { name: /내 검증/ }));
    const drawer = screen.getByText("내 검증 실행하기").closest("details")!;
    expect(drawer).toHaveAttribute("open");
    expect(
      await screen.findByRole("heading", {
        level: 1,
        name: "새 검증은 기준선과 무엇이 달라졌나요?",
      }),
    ).toBeInTheDocument();
    // 서랍은 결과보다 위에 있다.
    expect(
      drawer.compareDocumentPosition(
        screen.getByRole("heading", { level: 1 }),
      ) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
    expect(
      screen.getByText(/채점 검증 · 채택 판정 대상이 아닙니다/),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: /^판정이 바뀐 질문 \d+개$/ }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("list", { name: "적용 조건" }),
    ).not.toBeInTheDocument();
    expect(screen.getByText(/추가 모델 호출 비용/)).toHaveTextContent(/없/);
    // 같은 답변을 같은 규칙으로 다시 채점했으니 변화 0이 정상이라는 설명과 PR 관문 출처가 보여야 한다.
    expect(
      screen.getByText(
        /판정 변화 없음 · 채점 규칙을 바꾸지 않았다면 같은 결과가 정상입니다/,
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/offline-eval-regression-gate/),
    ).toBeInTheDocument();
  });
  it("공개 배포에는 로컬 개발 도구 구역이 없다", () => {
    render(<RegressionDashboard />);
    expect(
      screen.queryByRole("group", { name: "로컬 개발 도구" }),
    ).not.toBeInTheDocument();
    const experiments = within(
      screen.getByRole("group", { name: "실험 선택" }),
    );
    expect(experiments.getAllByRole("button")).toHaveLength(2);
    expect(screen.queryByText("내 검증 실행하기")).not.toBeInTheDocument();
  });
  it("재검색이 실제로 돌았는지 질문과 조건 줄에 함께 보여 준다", () => {
    render(<RegressionDashboard />);
    // q04는 재검색 없이 생성만 달라진 회귀다. 이 표시가 없으면 회귀를 재검색 탓으로 읽는다.
    const detail = within(
      screen.getByRole("region", { name: "q04 문항 상세" }),
    );
    expect(
      detail.getByText("재검색 실행 안 됨 · 처음 찾은 근거로 충분하다고 판단"),
    ).toBeInTheDocument();
    // 원래 기준은 회귀를 합계로 봐서 q04를 막지 않는다. 질문 단위 사실은 참고로 남긴다.
    expect(screen.getByText(/로 판정했다면/)).toHaveTextContent(
      /새로 실패 1개\(q04\)도 막는 조건.*재검색이 실행되지 않은 질문이라/,
    );
    expect(screen.getByText(/재검색 실제 실행 1\/42개/)).toBeInTheDocument();
  });
  it("회귀부터 선택하고 검색·필터가 동작하며 측정 실험만 맞바꾼다", () => {
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
      screen.getByRole("button", { name: /같은 질문의 반복 결과/ }),
    );
    fireEvent.click(
      screen.getByRole("button", { name: "기준선과 후보 맞바꾸기" }),
    );
    expect(screen.getByLabelText("기준선")).toHaveValue("run-2");
    expect(screen.getByLabelText("후보")).toHaveValue("run-1");
  });
  it("반복 측정은 채택 판정 없이 판정 일치 수와 흔들림을 보인다", () => {
    const suite = regressionSuites.find((item) => item.id === "reliability")!;
    const analysis = compareRuns(suite.runs[0], suite.runs[1]);
    const flipped = analysis.counts.regressed + analysis.counts.improved;
    render(<RegressionDashboard />);
    fireEvent.click(
      screen.getByRole("button", { name: /같은 질문의 반복 결과/ }),
    );
    expect(
      screen.getByRole("heading", {
        name: `질문별 판정 일치 ${analysis.total - flipped}/${analysis.total}`,
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/안정성 측정 · 채택 판정 대상이 아닙니다/),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("list", { name: "적용 조건" }),
    ).not.toBeInTheDocument();
    for (const badge of ["원래 기준 미충족", "검토 필요", "조건 충족"])
      expect(screen.queryByText(badge)).not.toBeInTheDocument();
    expect(screen.queryByText(/허용 \+50%/)).not.toBeInTheDocument();
    // 측정 실험에서 통과 → 실패를 회귀라고 부르면 도입을 막는 결함처럼 읽힌다.
    expect(document.querySelector("main")!.textContent).not.toMatch(/회귀/);
    expect(
      screen.getByRole("button", { name: /^흔들림 \(통과→실패\)/ }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/채택 정책을 적용하지 않습니다/),
    ).toBeInTheDocument();
    // 이 기록은 실행 시각을 남기지 않았다. 시각을 지어내지 않고 없다고 보인다.
    const compared = within(screen.getByLabelText("비교한 실행"));
    expect(compared.getAllByText(/실행 시각 기록 없음/)).toHaveLength(2);
  });
  it("반복 측정은 별도 세트로 고르고 실제 답변을 나란히 본다", () => {
    render(<RegressionDashboard />);
    fireEvent.click(
      screen.getByRole("button", { name: /같은 질문의 반복 결과/ }),
    );
    expect(screen.getByLabelText("기준선")).toHaveValue("run-1");
    expect(screen.getByLabelText("q06 기준선 답변")).toHaveTextContent(
      "48시간",
    );
    expect(screen.getByLabelText("q06 후보 답변")).toHaveTextContent("48시간");
    expect(screen.getByText("기대 표현 / 2시간")).toBeInTheDocument();
  });
  it("같은 실행 선택 시 지표를 숨기고 내보내기를 막는다", () => {
    render(<RegressionDashboard />);
    fireEvent.click(
      screen.getByRole("button", { name: /같은 질문의 반복 결과/ }),
    );
    fireEvent.change(screen.getByLabelText("후보"), {
      target: { value: "run-1" },
    });
    expect(screen.getByRole("alert")).toHaveTextContent("같은 실행");
    expect(
      screen.queryByRole("list", { name: "적용 조건" }),
    ).not.toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "비교 결과 JSON" }),
    ).toBeDisabled();
    expect(
      screen.queryByRole("textbox", { name: "판단 근거" }),
    ).not.toBeInTheDocument();
  });
  it("브라우저에 남은 기준값과 메모를 읽지도 쓰지도 않는다", () => {
    const getItem = vi.fn(() =>
      JSON.stringify({ cost: "999", latency: "999", decision: "adopt" }),
    );
    const setItem = vi.fn();
    vi.stubGlobal("localStorage", { getItem, setItem, removeItem: vi.fn() });
    render(<RegressionDashboard />);
    for (const name of ["research", "reliability"]) {
      if (name === "reliability")
        fireEvent.click(
          screen.getByRole("button", { name: /같은 질문의 반복 결과/ }),
        );
      expect(screen.queryByRole("spinbutton")).not.toBeInTheDocument();
      expect(
        screen.queryByRole("textbox", { name: "판단 근거" }),
      ).not.toBeInTheDocument();
    }
    expect(getItem).not.toHaveBeenCalled();
    expect(setItem).not.toHaveBeenCalled();
  });
  it("정책 v1은 읽기 전용으로 보이고 공식 판정과 구분된 참고 판정을 낸다", () => {
    render(<RegressionDashboard />);
    expect(screen.getByText(/로 판정했다면/)).toHaveTextContent(
      /정책 adoption-v1로 판정했다면 채택 불가 · 막는 조건 3개\(새로 실패 1개, 통과 수 39 → 39, 비용 \+66\.4%\)/,
    );
    expect(screen.getByText("원래 기준 미충족")).toBeInTheDocument();
    const criteria = within(
      screen.getByRole("region", { name: "판정 기준 (읽기 전용)" }),
    );
    expect(
      criteria.getByText(/이후 도입 실험의 기본 기준/),
    ).toBeInTheDocument();
    expect(criteria.getByText(/질문 단위/)).toBeInTheDocument();
    expect(criteria.getByText(/바꿀 수 없습니다/)).toBeInTheDocument();
  });
  it("스냅샷 문자열의 HTML은 실행되지 않고 글자 그대로 보인다", () => {
    const research = structuredClone(
      regressionSuites.find((suite) => suite.id === "research")!,
    );
    const html = '<img src=x onerror="alert(1)"> 결정 근거';
    research.experiment!.decision!.rationale = html;
    research.experiment!.criteria!.name = "<b>기준</b>";
    const { container } = render(<RegressionDashboard suites={[research]} />);
    expect(screen.getByText(html)).toBeInTheDocument();
    expect(screen.getByText("<b>기준</b>")).toBeInTheDocument();
    expect(container.querySelector("main img")).toBeNull();
  });
  it("기준 출처 시각을 확인할 수 없으면 사전 등록으로 표시하지 않는다", () => {
    const research = structuredClone(
      regressionSuites.find((suite) => suite.id === "research")!,
    );
    Object.assign(research.experiment!.criteria!, {
      source_commit: null,
      source_first_commit_at: null,
      preregistered: null,
    });
    render(<RegressionDashboard suites={[research]} />);
    const provenance = within(screen.getByLabelText("판정 기준과 결정"));
    expect(
      provenance.getByText(
        /기록 시점을 확인할 수 없음 · 사전 등록으로 표시하지 않음/,
      ),
    ).toBeInTheDocument();
    expect(
      provenance.getByText(/기준 출처의 커밋 기록 없음/),
    ).toBeInTheDocument();
    expect(provenance.queryByText(/^사전 등록 ·/)).not.toBeInTheDocument();
  });
  it("빈 데이터도 설명한다", () => {
    render(<RegressionDashboard suites={[]} />);
    expect(
      screen.getByRole("heading", { name: "평가 실행을 준비해 주세요" }),
    ).toBeInTheDocument();
  });
});

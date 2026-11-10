import {
  fireEvent,
  render,
  screen,
  within,
  waitFor,
} from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { GoldenReviewPage } from "@/components/GoldenReviewPage";
import {
  AdditionalAiReview,
  type JudgeSnapshot,
} from "@/components/GoldenJudgePanel";

it("AI 추가 검토는 사람 판정 입력과 별도로 이유와 인용을 보여준다", () => {
  const item = {
    verdict: "fail",
    reason: "적용 지역 설명이 충돌합니다.",
    answer_quote: "수도권 외는 알 수 없습니다.",
    evidence: [{ anchor: "src:s1", quote: "수도권에서만 제공한다." }],
  };
  render(
    <AdditionalAiReview
      review={{
        metrics: {
          facts: item,
          citation_accuracy: item,
          citation_coverage: item,
          refusal: { ...item, verdict: "not_applicable" },
        },
      }}
    />,
  );
  fireEvent.click(screen.getByText("AI 추가 검토 보기"));
  expect(screen.getByText(/사람 판정과 별도/)).toBeInTheDocument();
  expect(screen.getByText("사실 일치 · 실패")).toBeInTheDocument();
  expect(screen.queryByRole("combobox")).not.toBeInTheDocument();
});

afterEach(() => vi.unstubAllGlobals());
function data(): JudgeSnapshot {
  return {
    dataset: {
      version: "v1",
      documents: [
        {
          id: "doc",
          title: "원문 규정",
          text: "일반 입고 검수는 2시간 안에 끝내야 합니다.",
        },
      ],
      questions: [1, 2].map((n) => ({
        id: `g0${n}`,
        query: `검수 질문 ${n}`,
        kind: "fact",
        expected_facts: ["2시간"],
        allowed_expressions: ["동의어 허용"],
        answerable: true,
        fingerprint: `q${n}`,
        evidence: [{ doc_id: "doc", start: 0, end: 30 }],
      })),
    },
    samples: [
      {
        id: "real-1",
        question_id: "g01",
        origin: "stored",
        label: "실제 저장 실행",
        fingerprint: "sample1",
        answer: "검수는 48시간입니다.",
        supplied_evidence: null,
        code: { verdict: "fail", reason: "기대 사실 누락" },
        citation_validity: {
          verdict: "review_needed",
          reason: "원본 근거 맵 없음",
        },
      },
    ],
    results: {},
    reviews: {},
    models: [],
    busy: false,
    max_budget_micros: 2000000,
    jobs: [],
    agreement: { synthetic: {}, stored: {} } as JudgeSnapshot["agreement"],
  };
}
async function open(ok = true) {
  const value = data();
  const fetcher = vi.fn().mockImplementation((_url, opts) => {
    if (opts?.method === "POST") {
      if (!ok)
        return Promise.resolve(
          Response.json(
            { error: "저장 충돌. 다시 확인하세요." },
            { status: 409 },
          ),
        );
      const payload = JSON.parse(opts.body);
      value.reviews[payload.target] = {
        revision: 1,
        reason: payload.reason,
        metrics: payload.metrics,
        saved_at: "2026-11-10T00:00:00Z",
      };
      return Promise.resolve(Response.json({ saved: true }));
    }
    return Promise.resolve(Response.json(value));
  });
  vi.stubGlobal("fetch", fetcher);
  render(<GoldenReviewPage enabled />);
  await screen.findByRole("heading", { name: "검수 질문 1" });
  return fetcher;
}
describe("집중 검토 페이지", () => {
  it("운영 상태에서는 로컬 기록을 요청하지 않는다", () => {
    const fetcher = vi.fn();
    vi.stubGlobal("fetch", fetcher);
    render(<GoldenReviewPage enabled={false} />);
    expect(fetcher).not.toHaveBeenCalled();
    expect(screen.getByText(/사람 검토는 로컬 개발 환경/)).toBeInTheDocument();
  });
  it("정답·원문·저장 폼을 바로 보여주고 문항을 이동한다", async () => {
    const fetcher = await open();
    expect(screen.getByRole("region", { name: "정답 기준" })).toHaveTextContent(
      "2시간",
    );
    expect(screen.getByRole("region", { name: "정답 원문" })).toHaveTextContent(
      "일반 입고 검수는 2시간",
    );
    expect(
      screen.getByRole("button", { name: "골든셋 후보 검토 저장" }),
    ).toBeVisible();
    expect(screen.queryByText("선택한 저장 답변 심사 · 유료")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "다음 문항" }));
    expect(
      screen.getByRole("heading", { name: "검수 질문 2" }),
    ).toBeInTheDocument();
    expect(fetcher.mock.calls.every((c) => !c[1]?.method)).toBe(true);
  });
  it("작성 중 문항 변경을 막고 취소하면 다시 이동한다", async () => {
    await open();
    fireEvent.change(screen.getByLabelText("검토 근거"), {
      target: { value: "대조 중" },
    });
    expect(screen.getByRole("button", { name: "다음 문항" })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "작성 취소" }));
    expect(screen.getByLabelText("검토 근거")).toHaveValue("");
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "다음 문항" })).toBeEnabled(),
    );
  });
  it("기존 저장 API에 동일 지문으로 사람 검토를 보낸다", async () => {
    const fetcher = await open();
    fireEvent.click(
      screen.getByLabelText("질문·기대 사실·원문 근거를 직접 확인했습니다."),
    );
    fireEvent.change(screen.getByLabelText("검토 근거"), {
      target: { value: "원문의 2시간과 일치" },
    });
    fireEvent.click(
      screen.getByRole("button", { name: "골든셋 후보 검토 저장" }),
    );
    await screen.findByText("검토를 로컬 디스크에 저장했습니다.");
    const request = fetcher.mock.calls.find((c) => c[1]?.method === "POST");
    expect(JSON.parse(request![1].body)).toMatchObject({
      action: "judge-review",
      kind: "question",
      target: "q1",
      metrics: { verified: true },
    });
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "다음 문항" })).toBeEnabled(),
    );
  });
  it("실제 답변 채점은 별도 모드이며 근거 누락을 알린다", async () => {
    await open();
    fireEvent.click(screen.getByRole("button", { name: "AI 답변 채점" }));
    expect(screen.getByLabelText("답변 출처")).toHaveValue("stored");
    expect(
      screen.getByRole("region", { name: "검토할 AI 답변" }),
    ).toHaveTextContent("48시간");
    expect(
      screen.getByText(/생성 당시 인용 근거가 저장되지 않았습니다/),
    ).toBeInTheDocument();
    const form = screen
      .getByRole("button", { name: "이 답변의 사람 판정 저장" })
      .closest("form")!;
    expect(within(form).getByLabelText("사실 일치")).toHaveValue("");
  });
  it("저장 실패 시 작성한 내용을 잃지 않는다", async () => {
    await open(false);
    fireEvent.click(
      screen.getByLabelText("질문·기대 사실·원문 근거를 직접 확인했습니다."),
    );
    fireEvent.change(screen.getByLabelText("검토 근거"), {
      target: { value: "보존할 검토" },
    });
    fireEvent.click(
      screen.getByRole("button", { name: "골든셋 후보 검토 저장" }),
    );
    expect(await screen.findByRole("alert")).toHaveTextContent("저장 충돌");
    expect(screen.getByLabelText("검토 근거")).toHaveValue("보존할 검토");
    expect(screen.getByRole("button", { name: "다음 문항" })).toBeDisabled();
  });
});

// #266 · golden-answer-judge: 유료 호출과 실제 사람 라벨 없이 상태·제출 계약 검증.
import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { act } from "react";
import {
  GoldenJudgePanel,
  type JudgeSnapshot,
} from "@/components/GoldenJudgePanel";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
  vi.useRealTimers();
});
const keys = [
  "facts",
  "citation_accuracy",
  "citation_coverage",
  "refusal",
] as const;
function snapshot(): JudgeSnapshot {
  const stats = Object.fromEntries(
    keys.map((k) => [
      k,
      { paired: 0, excluded: 1, agreement: null, false_pass: 0, false_fail: 0 },
    ]),
  ) as JudgeSnapshot["agreement"]["stored"];
  return {
    dataset: {
      version: "golden-v1",
      documents: [
        {
          id: "doc",
          title: "테스트 원문",
          text: "입고 검수는 2시간 안에 끝낸다.",
        },
      ],
      questions: [
        {
          id: "g01",
          query: "검수 기한은?",
          kind: "fact",
          expected_facts: ["2시간"],
          allowed_expressions: ["의미가 같으면 허용"],
          answerable: true,
          fingerprint: "question-fp",
          evidence: [{ doc_id: "doc", start: 0, end: 20 }],
        },
      ],
    },
    samples: [
      {
        id: "example-g01",
        question_id: "g01",
        origin: "synthetic",
        label: "검증용 합성 답변",
        fingerprint: "sample-fp",
        answer: "2시간 [[src:doc]]",
        supplied_evidence: { "src:doc": "입고 검수는 2시간 안에 끝낸다." },
        code: null,
        citation_validity: { verdict: "pass", reason: "제공 표식 대조" },
      },
    ],
    results: {},
    reviews: {},
    models: [],
    busy: false,
    max_budget_micros: 2000000,
    jobs: [],
    agreement: { synthetic: stats, stored: stats },
  };
}
async function open(data = snapshot(), postOk = true) {
  const fetcher = vi
    .fn()
    .mockImplementation((_url, opts) =>
      Promise.resolve(
        opts?.method === "POST"
          ? Response.json(
              postOk ? { saved: true } : { error: "검토 저장 충돌" },
              { status: postOk ? 200 : 409 },
            )
          : Response.json(data),
      ),
    );
  vi.stubGlobal("fetch", fetcher);
  render(<GoldenJudgePanel enabled />);
  fireEvent.click(screen.getByText("골든셋과 AI 심사"));
  await screen.findByText("30문항 중 0문항을 사람이 검토했습니다.");
  return fetcher;
}

describe("골든셋 로컬 작업대", () => {
  it("갱신된 사람 판정으로 작성 중 개정 번호를 자동 승격하지 않는다", async () => {
    const interval = vi.spyOn(globalThis, "setInterval");
    const data = snapshot();
    const fetcher = await open(data);
    fireEvent.click(screen.getByText("이 답변의 사람 판정 남기기"));
    const button = screen.getByRole("button", {
      name: "이 답변의 사람 판정 저장",
    });
    const form = button.closest("form")!;
    fireEvent.change(within(form).getByLabelText("검토 근거"), {
      target: { value: "작성 중인 검토" },
    });
    data.reviews["sample-fp"] = {
      revision: 1,
      saved_at: "2026-11-10T00:00:00Z",
      reason: "다른 제출",
      metrics: { facts: "fail" },
    };
    await act(async () => {
      const callback = interval.mock.calls.find(
        (call) => call[1] === 3000,
      )![0] as () => void;
      callback();
    });
    expect(
      await screen.findByText(/다른 검토가 저장됐습니다/),
    ).toBeInTheDocument();
    expect(button).toBeDisabled();
    expect(within(form).getByLabelText("검토 근거")).toHaveValue(
      "작성 중인 검토",
    );
    expect(fetcher.mock.calls.every((c) => c[1]?.method !== "POST")).toBe(true);
  });
  it("비활성 상태나 닫힌 상태에서 연결하지 않는다", () => {
    const fetcher = vi.fn();
    vi.stubGlobal("fetch", fetcher);
    const { unmount } = render(<GoldenJudgePanel enabled={false} />);
    expect(fetcher).not.toHaveBeenCalled();
    unmount();
    render(<GoldenJudgePanel enabled />);
    expect(fetcher).not.toHaveBeenCalled();
  });
  it("사람 판정과 심사 결과를 생성하지 않고 미측정을 표시한다", async () => {
    const fetcher = await open();
    expect(screen.getAllByText("사람 미검토").length).toBeGreaterThan(0);
    expect(screen.getAllByText("미측정")).toHaveLength(4);
    expect(
      screen.getByRole("region", { name: "기대한 사실" }),
    ).toHaveTextContent("2시간");
    expect(fetcher.mock.calls.every((call) => !call[1]?.method)).toBe(true);
    fireEvent.click(screen.getByText("저장 답변을 AI로 심사하기 · 유료"));
    expect(
      screen.getByRole("button", { name: "선택한 저장 답변 심사 · 유료" }),
    ).toBeDisabled();
    expect(
      screen.getByText(/심사 모델이 준비되지 않았습니다/),
    ).toBeInTheDocument();
  });
  it("직접 선택과 이유 없이는 사람 판정을 제출하지 않는다", async () => {
    const fetcher = await open();
    fireEvent.click(screen.getByText("이 답변의 사람 판정 남기기"));
    const button = screen.getByRole("button", {
      name: "이 답변의 사람 판정 저장",
    });
    expect(button).toBeDisabled();
    const form = button.closest("form")!;
    for (const label of [
      "사실 일치",
      "인용 정확도",
      "주요 주장 인용 충실도",
      "거절 적절성",
    ])
      fireEvent.change(within(form).getByLabelText(label), {
        target: { value: "pass" },
      });
    fireEvent.change(within(form).getByLabelText("검토 근거"), {
      target: { value: "기대 사실과 원문을 직접 대조한 테스트" },
    });
    fireEvent.click(button);
    await screen.findByText("검토를 로컬 디스크에 저장했습니다.");
    const call = fetcher.mock.calls.find((call) => call[1]?.method === "POST");
    expect(JSON.parse(call![1].body)).toMatchObject({
      action: "judge-review",
      kind: "sample",
      target: "sample-fp",
      revision: 0,
      metrics: { facts: "pass" },
    });
  });
  it("저장 충돌을 성공으로 표시하지 않는다", async () => {
    await open(snapshot(), false);
    fireEvent.click(screen.getByText("정답 원문 근거와 후보 검토"));
    fireEvent.click(
      screen.getByLabelText("질문·기대 사실·원문 근거를 직접 확인했습니다."),
    );
    const button = screen.getByRole("button", {
      name: "골든셋 후보 검토 저장",
    });
    fireEvent.change(
      within(button.closest("form")!).getByLabelText("검토 근거"),
      { target: { value: "검토 테스트" } },
    );
    fireEvent.click(button);
    await screen.findByRole("alert");
    expect(screen.getByRole("alert")).toHaveTextContent("검토 저장 충돌");
    expect(screen.queryByText("검토를 로컬 디스크에 저장했습니다.")).toBeNull();
  });
  it("불일치와 미검토 필터 및 출처를 분리한다", async () => {
    const data = snapshot();
    data.reviews["sample-fp"] = {
      revision: 1,
      saved_at: "2026-11-10T00:00:00Z",
      reason: "테스트",
      metrics: { facts: "fail" },
    };
    data.results["sample-fp"] = {
      status: "evaluated",
      metrics: { facts: { verdict: "pass", reason: "테스트 심사" } },
    };
    await open(data);
    fireEvent.change(screen.getByLabelText("검토할 표본"), {
      target: { value: "disagreed" },
    });
    expect(
      screen.getByRole("heading", { name: "검수 기한은?" }),
    ).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("검토할 표본"), {
      target: { value: "unreviewed" },
    });
    expect(screen.getByText(/이 조건의 표본이 없습니다/)).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("답변 출처"), {
      target: { value: "stored" },
    });
    expect(
      screen.getByText(/현재 출처: 저장된 실제 모델 답변/),
    ).toBeInTheDocument();
  });
  it("조회와 별개로 선택 모델·예산으로 명시적 심사를 요청한다", async () => {
    const data = snapshot();
    data.models = ["test/model"];
    const fetcher = await open(data);
    fireEvent.click(screen.getByText("저장 답변을 AI로 심사하기 · 유료"));
    fireEvent.change(screen.getByLabelText("심사 모델"), {
      target: { value: "test/model" },
    });
    fireEvent.click(
      screen.getByRole("button", { name: "선택한 저장 답변 심사 · 유료" }),
    );
    await waitFor(() =>
      expect(fetcher.mock.calls.some((c) => c[1]?.method === "POST")).toBe(
        true,
      ),
    );
    const call = fetcher.mock.calls.find((c) => c[1]?.method === "POST");
    expect(JSON.parse(call![1].body)).toEqual({
      action: "judge-run",
      model: "test/model",
      budget_micros: 200000,
      sample_ids: ["example-g01"],
    });
  });
});

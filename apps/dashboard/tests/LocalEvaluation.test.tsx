import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { LocalEvaluationPanel } from "@/components/LocalEvaluationPanel";
import { GET, POST } from "@/app/api/local-evaluation/route";

vi.mock("node:fs/promises", () => {
  const readFile = vi.fn().mockResolvedValue("test-token");
  return { readFile, default: { readFile } };
});
afterEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
});
const snapshot = {
  runs: [],
  jobs: [],
  baseline_id: null,
  model_ready: false,
  max_budget_micros: 2000000,
};

describe("로컬 실행 경계", () => {
  it("심사 조회·검토는 고정 로컬 경로에만 전달한다", async () => {
    vi.stubEnv("NODE_ENV", "development");
    vi.stubEnv("LOCAL_EVALUATION_ENABLED", "1");
    const fetcher = vi
      .fn()
      .mockImplementation(() =>
        Promise.resolve(Response.json({ saved: true })),
      );
    vi.stubGlobal("fetch", fetcher);
    expect(
      (
        await GET(
          new Request("http://127.0.0.1:54410/api/local-evaluation?view=judge"),
        )
      ).status,
    ).toBe(200);
    expect(fetcher.mock.calls[0][0]).toBe(
      "http://127.0.0.1:54411/judge/status",
    );
    expect(
      (
        await POST(
          new Request("http://127.0.0.1:54410/api/local-evaluation", {
            method: "POST",
            headers: { origin: "http://127.0.0.1:54410" },
            body: JSON.stringify({
              action: "judge-review",
              kind: "sample",
              id: "x",
            }),
          }),
        )
      ).status,
    ).toBe(200);
    expect(fetcher.mock.calls[1][0]).toBe(
      "http://127.0.0.1:54411/judge/reviews",
    );
    vi.stubEnv("NODE_ENV", "production");
    expect(
      (
        await GET(
          new Request("http://127.0.0.1:54410/api/local-evaluation?view=judge"),
        )
      ).status,
    ).toBe(403);
  });
  it("운영·미활성 개발·외부 origin은 요청을 전달하지 않는다", async () => {
    const fetcher = vi.fn();
    vi.stubGlobal("fetch", fetcher);
    vi.stubEnv("NODE_ENV", "production");
    vi.stubEnv("LOCAL_EVALUATION_ENABLED", "1");
    expect(
      (await GET(new Request("http://127.0.0.1:54410/api/local-evaluation")))
        .status,
    ).toBe(403);
    vi.stubEnv("NODE_ENV", "development");
    vi.stubEnv("LOCAL_EVALUATION_ENABLED", "0");
    expect(
      (await GET(new Request("http://127.0.0.1:54410/api/local-evaluation")))
        .status,
    ).toBe(403);
    vi.stubEnv("LOCAL_EVALUATION_ENABLED", "1");
    expect(
      (
        await POST(
          new Request("http://127.0.0.1:54410/api/local-evaluation", {
            method: "POST",
            headers: { origin: "https://evil.example" },
            body: '{"action":"run"}',
          }),
        )
      ).status,
    ).toBe(403);
    expect(fetcher).not.toHaveBeenCalled();
  });
  it("루프백의 고정 경로에만 인증 토큰을 전달한다", async () => {
    vi.stubEnv("NODE_ENV", "development");
    vi.stubEnv("LOCAL_EVALUATION_ENABLED", "1");
    const fetcher = vi.fn().mockResolvedValue(Response.json(snapshot));
    vi.stubGlobal("fetch", fetcher);
    const response = await GET(
      new Request("http://127.0.0.1:54410/api/local-evaluation"),
    );
    expect(await response.clone().json()).toEqual(snapshot);
    expect(fetcher.mock.calls[0][0]).toBe("http://127.0.0.1:54411/status");
    expect(fetcher.mock.calls[0][1].headers["X-Evaluation-Token"]).toBe(
      "test-token",
    );
    expect(
      JSON.stringify(await response.clone().json()).includes("test-token"),
    ).toBe(false);
  });
  it("Next 내부 URL과 실제 루프백 Host가 다를 때도 실제 동일 출처만 허용한다", async () => {
    vi.stubEnv("NODE_ENV", "development");
    vi.stubEnv("LOCAL_EVALUATION_ENABLED", "1");
    const fetcher = vi.fn().mockResolvedValue(Response.json({ saved: true }));
    vi.stubGlobal("fetch", fetcher);
    const response = await POST(
      new Request("http://localhost:54410/api/local-evaluation", {
        method: "POST",
        headers: { host: "127.0.0.1:54410", origin: "http://127.0.0.1:54410" },
        body: JSON.stringify({ action: "baseline", run_id: "seed" }),
      }),
    );
    expect(response.status).toBe(200);
    expect(fetcher.mock.calls[0][0]).toBe("http://127.0.0.1:54411/baseline");
  });
});

describe("로컬 평가 실행 패널", () => {
  it("비활성 상태에서는 연결하지 않는다", () => {
    const fetcher = vi.fn();
    vi.stubGlobal("fetch", fetcher);
    render(<LocalEvaluationPanel enabled={false} onSuite={vi.fn()} />);
    expect(fetcher).not.toHaveBeenCalled();
  });
  it("무료 실행을 요청하고 유료 준비가 없으면 비활성 표시한다", async () => {
    const fetcher = vi
      .fn()
      .mockImplementation((_url, options) =>
        Promise.resolve(
          Response.json(options?.method === "POST" ? { id: "job" } : snapshot),
        ),
      );
    vi.stubGlobal("fetch", fetcher);
    render(<LocalEvaluationPanel enabled onSuite={vi.fn()} />);
    const drawer = screen.getByText("새 검사 시작").closest("details")!;
    expect(drawer).not.toHaveAttribute("open");
    fireEvent.click(screen.getByText("새 검사 시작"));
    await screen.findByText("접속됨 · 결과는 로컬 디스크에 보존");
    expect(
      screen.getByRole("option", { name: /AI 답변 새로 만들기/ }),
    ).toBeDisabled();
    fireEvent.change(screen.getByLabelText("검사 이름"), {
      target: { value: "채점기 재검증" },
    });
    fireEvent.click(
      screen.getByRole("button", { name: "다시 채점하기 · 무료" }),
    );
    await waitFor(() =>
      expect(
        fetcher.mock.calls.some((call) => call[1]?.method === "POST"),
      ).toBe(true),
    );
    const call = fetcher.mock.calls.find((call) => call[1]?.method === "POST");
    expect(JSON.parse(call![1].body)).toMatchObject({
      action: "run",
      mode: "rescore",
      label: "채점기 재검증",
    });
  });
});

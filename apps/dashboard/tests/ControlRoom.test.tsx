import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const apiFetch = vi.fn();

vi.mock("@/lib/api-client", () => ({
  ApiError: class ApiError extends Error {},
  apiFetch: (...args: unknown[]) => apiFetch(...args),
}));

import { ControlRoom } from "@/components/ControlRoom";

const ASK_TRACE = "7f3a19c2-1111-4222-8333-444455556666";
const INGEST_TRACE = "8a3a19c2-1111-4222-8333-444455556666";

const askSummary = {
  trace_id: ASK_TRACE,
  kind: "ask",
  status: "resolved",
  started_at: "2026-11-02T00:00:00+00:00",
  route: { decision: "STANDARD", reason: "default" },
  total_ms: 1200,
};

const ingestSummary = {
  trace_id: INGEST_TRACE,
  kind: "ingest",
  status: "running",
  started_at: "2026-11-01T00:00:00+00:00",
  route: null,
  total_ms: null,
};

const askDetail = {
  ...askSummary,
  spans: [
    { name: "retrieval", label: "4채널 검색", start_ms: 0, duration_ms: 200 },
    { name: "llm_stream", label: "답변 생성", start_ms: 200, duration_ms: 1000 },
  ],
  stages: [],
  calls: [
    {
      call: "ask",
      kind: "llm",
      model: "test-model",
      attempt: null,
      incomplete: true,
      total_tokens: 100,
      cost_micros: 2300,
      duration_ms: 1000,
      occurred_at: "2026-11-02T00:00:01+00:00",
    },
  ],
  totals: {
    call_count: 1,
    total_tokens: 100,
    cost_micros: 2300,
    incomplete_call_count: 1,
  },
  missing_channels: ["wiki_vector"],
};

const ingestDetail = {
  ...ingestSummary,
  spans: [],
  stages: [
    {
      type: "parse",
      label: "원문 파싱",
      state: "completed",
      attempts: 1,
      duration_ms: 500,
      error_category: null,
    },
    {
      type: "compile",
      label: "위키 컴파일",
      state: "active",
      attempts: 1,
      duration_ms: null,
      error_category: null,
    },
    {
      type: "embed",
      label: "임베딩",
      state: "pending",
      attempts: 0,
      duration_ms: null,
      error_category: null,
    },
  ],
  calls: [],
  totals: {
    call_count: 0,
    total_tokens: 0,
    cost_micros: 0,
    incomplete_call_count: 0,
  },
};

function respond(routes: Record<string, unknown>) {
  apiFetch.mockImplementation(async (path: string) => {
    for (const [suffix, value] of Object.entries(routes)) {
      if (path.endsWith(suffix)) {
        if (value instanceof Error) throw value;
        return value;
      }
    }
    throw new Error(`unexpected path ${path}`);
  });
}

beforeEach(() => {
  apiFetch.mockReset();
});

describe("ControlRoom", () => {
  it("빈 워크스페이스에서 첫 trace가 생기는 방법을 안내한다", async () => {
    respond({
      "/control/traces": { items: [], can_view_workspace: false },
    });

    render(<ControlRoom workspaceId="ws" />);

    const empty = await screen.findByTestId("control-empty");
    expect(empty).toHaveTextContent("질문을 하거나 원문을 등록하면");
  });

  it("Ask trace의 구간과 합계, 미완료 호출 경고를 보여준다", async () => {
    respond({
      "/control/traces": { items: [askSummary], can_view_workspace: false },
      [`/control/traces/${ASK_TRACE}`]: askDetail,
    });

    render(<ControlRoom workspaceId="ws" />);

    const detail = await screen.findByRole("article", { name: "trace 상세" });
    const timeline = within(detail).getByRole("region", {
      name: "구간 타임라인",
    });
    expect(timeline).toHaveTextContent("4채널 검색");
    expect(timeline).toHaveTextContent("답변 생성");
    expect(detail).toHaveTextContent("STANDARD");
    expect(detail).toHaveTextContent("$0.0023");
    expect(detail).toHaveTextContent("최종 사용량을 받지 못한 호출이");
    expect(detail).toHaveTextContent("실패한 검색 채널: wiki_vector");
    expect(detail).toHaveTextContent("ask (미완료)");
  });

  it("viewer에게는 집계를 요청하지도 표시하지도 않는다", async () => {
    respond({
      "/control/traces": { items: [askSummary], can_view_workspace: false },
      [`/control/traces/${ASK_TRACE}`]: askDetail,
    });

    render(<ControlRoom workspaceId="ws" />);

    await screen.findByRole("article", { name: "trace 상세" });
    expect(screen.queryByRole("region", { name: /질문 집계/ })).toBeNull();
    expect(
      apiFetch.mock.calls.some(([path]) =>
        String(path).includes("ask-aggregate"),
      ),
    ).toBe(false);
  });

  it("editor는 집계와 수집 단계의 상태 구분을 본다", async () => {
    respond({
      "/control/traces": {
        items: [ingestSummary],
        can_view_workspace: true,
      },
      "/control/ask-aggregate": {
        days: 30,
        turn_count: 2,
        resolved_count: 2,
        no_evidence_count: 0,
        error_count: 0,
        decision_counts: { STANDARD: 2 },
        p50_total_ms: 1200,
        p95_total_ms: 1500,
        total_cost_micros: 4000,
        incomplete_call_count: 0,
      },
      [`/control/traces/${INGEST_TRACE}`]: ingestDetail,
    });

    render(<ControlRoom workspaceId="ws" />);

    const aggregate = await screen.findByRole("region", {
      name: "최근 30일 질문 집계",
    });
    expect(aggregate).toHaveTextContent("2건");
    expect(aggregate).toHaveTextContent("STANDARD 2");
    const stages = await screen.findByRole("list", { name: "처리 단계" });
    const items = within(stages).getAllByRole("listitem");
    expect(items[0]).toHaveTextContent("원문 파싱");
    expect(items[0]).toHaveTextContent("완료");
    expect(items[1]).toHaveTextContent("진행 중");
    expect(items[2]).toHaveTextContent("대기");
  });

  it("권한이 없는 trace는 값 없이 안내만 한다", async () => {
    respond({
      "/control/traces": { items: [askSummary], can_view_workspace: false },
      [`/control/traces/${ASK_TRACE}`]: new Error("403"),
    });

    render(<ControlRoom workspaceId="ws" />);

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "이 trace를 볼 수 없습니다.",
    );
    expect(screen.queryByRole("article", { name: "trace 상세" })).toBeNull();
  });

  it("이후 Step 탭은 지어낸 수치 없이 빈 상태만 표시한다", async () => {
    respond({
      "/control/traces": { items: [], can_view_workspace: false },
    });
    const user = userEvent.setup();

    render(<ControlRoom workspaceId="ws" />);
    await waitFor(() => expect(apiFetch).toHaveBeenCalled());

    await user.click(screen.getByRole("tab", { name: "예산" }));

    const panel = screen.getByRole("tabpanel");
    expect(panel).toHaveTextContent("Step 2에서 수집을 시작합니다");
    expect(panel).toHaveTextContent("아직 수집된 데이터가 없습니다.");
    expect(panel.textContent).not.toMatch(/\d+%|\$\d/);
  });
});

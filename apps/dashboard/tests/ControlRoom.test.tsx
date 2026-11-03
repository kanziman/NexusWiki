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
    {
      name: "llm_stream",
      label: "답변 생성",
      start_ms: 200,
      duration_ms: 1000,
    },
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
  it("미확정 점유와 공급자 보고액을 구분하고 운영자 확인을 안내한다", async () => {
    respond({
      "/control/traces": { items: [askSummary], can_view_workspace: false },
      [`/control/traces/${ASK_TRACE}`]: {
        ...askDetail,
        totals: {
          ...askDetail.totals,
          pending_micros: 10000,
          budget_micros: 12000,
          unresolved_count: 1,
          manual_review_count: 1,
          over_reserve_count: 1,
        },
      },
    });
    render(<ControlRoom workspaceId="ws" />);
    const detail = await screen.findByRole("article", { name: "trace 상세" });
    expect(
      within(detail).getByText("미확정 예산 점유").parentElement,
    ).toHaveTextContent("$0.0100");
    expect(
      within(detail).getByText("예산 판정액").parentElement,
    ).toHaveTextContent("$0.0120");
    expect(detail).toHaveTextContent("실제 청구액이 아닙니다");
    expect(detail).toHaveTextContent("운영자 확인");
    expect(detail).toHaveTextContent("확보액을 넘은 공급자 비용");
  });
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

  it("상세에 최종 상태와 호출별 Router 결정을 보여준다", async () => {
    const compileCall = {
      call: "compile",
      kind: "llm",
      model: "m",
      attempt: 1,
      incomplete: false,
      route: "SKIP_UNCHANGED",
      total_tokens: 10,
      cost_micros: 100,
      duration_ms: 5,
      occurred_at: "2026-11-02T00:00:00Z",
    };
    respond({
      "/control/traces": {
        items: [{ ...ingestSummary, status: "failed" }],
        can_view_workspace: true,
      },
      "/control/ask-aggregate": {
        days: 30,
        turn_count: 0,
        resolved_count: 0,
        no_evidence_count: 0,
        error_count: 0,
        decision_counts: {},
        p50_total_ms: null,
        p95_total_ms: null,
        total_cost_micros: 0,
        incomplete_call_count: 0,
      },
      [`/control/traces/${ingestSummary.trace_id}`]: {
        ...ingestDetail,
        status: "failed",
        calls: [compileCall],
        totals: {
          call_count: 1,
          total_tokens: 10,
          cost_micros: 100,
          incomplete_call_count: 0,
        },
      },
    });

    render(<ControlRoom workspaceId="ws" />);

    const detail = await screen.findByRole("article", { name: "trace 상세" });
    expect(
      within(detail).getByText("최종 상태").parentElement,
    ).toHaveTextContent("실패");
    const table = within(detail).getByRole("table", { name: "공급자 호출" });
    expect(table).toHaveTextContent("Router 결정");
    expect(table).toHaveTextContent("SKIP_UNCHANGED");
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

  it("예산 탭에서 editor에게 당월 예산 현황, 토큰 정책, 절감 카운트, 호출 경로별 내역을 표시한다", async () => {
    respond({
      "/control/traces": { items: [], can_view_workspace: true },
      "/control/ask-aggregate": {
        days: 30,
        turn_count: 0,
        resolved_count: 0,
        no_evidence_count: 0,
        error_count: 0,
        decision_counts: {},
        p50_total_ms: null,
        p95_total_ms: null,
        total_cost_micros: 0,
        incomplete_call_count: 0,
      },
      "/control/budget": {
        days: 30,
        can_view_workspace: true,
        month_start: "2026-11-01T00:00:00Z",
        cap_micros: 5000000,
        reported_micros: 12000,
        pending_micros: 3000,
        budget_micros: 15000,
        remaining_micros: 4985000,
        unresolved_count: 1,
        manual_review_count: 0,
        over_reserve_count: 0,
        policy: {
          ask_max_context_tokens: 6000,
          compile_max_input_tokens: 24000,
          compile_max_output_tokens: 4096,
          compile_max_pages: 8,
          conflict_max_input_tokens: 4000,
          conflict_max_output_tokens: 512,
        },
        savings: {
          ask_no_evidence_count: 3,
          ask_context_truncated_count: 2,
          compile_truncated_count: 1,
          compile_skipped_count: 4,
        },
        by_call_path: [
          {
            call: "compile",
            kind: "llm",
            call_count: 5,
            prompt_tokens: 10000,
            completion_tokens: 2000,
            total_tokens: 12000,
            reported_micros: 10000,
            pending_micros: 0,
            budget_micros: 10000,
          },
          {
            call: "ask",
            kind: "llm",
            call_count: 2,
            prompt_tokens: 800,
            completion_tokens: 200,
            total_tokens: 1000,
            reported_micros: 2000,
            pending_micros: 3000,
            budget_micros: 5000,
          },
        ],
      },
    });
    const user = userEvent.setup();

    render(<ControlRoom workspaceId="ws" />);
    await waitFor(() => expect(apiFetch).toHaveBeenCalled());

    await user.click(screen.getByRole("tab", { name: "예산" }));

    const monthly = await screen.findByRole("region", {
      name: "당월 예산 현황",
    });
    expect(monthly).toHaveTextContent("$5.0000");
    expect(monthly).toHaveTextContent("$0.0150");
    expect(monthly).toHaveTextContent("1건 / 0건");

    const policy = screen.getByRole("region", { name: "활성 토큰 예산 정책" });
    expect(policy).toHaveTextContent("6,000 토큰");
    expect(policy).toHaveTextContent("24,000 토큰");
    expect(policy).toHaveTextContent("4,096 토큰");

    const savings = screen.getByRole("region", {
      name: "최근 30일 예산 절감 실행",
    });
    expect(savings).toHaveTextContent("4건");

    const table = screen.getByRole("table", {
      name: "호출 경로별 비용 및 토큰",
    });
    expect(table).toHaveTextContent("위키 컴파일 (compile)");
    expect(table).toHaveTextContent("질문 답변 (ask)");
  });

  it("예산 탭에서 viewer에게는 월간 예산과 본인 절감 건수만 표시하고 호출 경로 표는 숨긴다", async () => {
    respond({
      "/control/traces": { items: [], can_view_workspace: false },
      "/control/budget": {
        days: 30,
        can_view_workspace: false,
        month_start: "2026-11-01T00:00:00Z",
        cap_micros: 5000000,
        reported_micros: 2000,
        pending_micros: 0,
        budget_micros: 2000,
        remaining_micros: 4998000,
        unresolved_count: 0,
        manual_review_count: 0,
        over_reserve_count: 0,
        policy: {
          ask_max_context_tokens: 6000,
          compile_max_input_tokens: 24000,
          compile_max_output_tokens: 4096,
          compile_max_pages: 8,
          conflict_max_input_tokens: 4000,
          conflict_max_output_tokens: 512,
        },
        savings: {
          ask_no_evidence_count: 1,
          ask_context_truncated_count: 1,
          compile_truncated_count: 0,
          compile_skipped_count: 0,
        },
        by_call_path: [],
      },
    });
    const user = userEvent.setup();

    render(<ControlRoom workspaceId="ws" />);
    await waitFor(() => expect(apiFetch).toHaveBeenCalled());

    await user.click(screen.getByRole("tab", { name: "예산" }));

    await screen.findByRole("region", { name: "당월 예산 현황" });
    expect(
      screen.getByText(
        /조회 전용\(viewer\) 멤버에게는 워크스페이스 월간 예산 현황과/,
      ),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("table", { name: "호출 경로별 비용 및 토큰" }),
    ).toBeNull();
  });

  it("품질 탭에서 editor에게 답변 인용 계약과 구조화 출력, 근거 집계를 표시한다", async () => {
    respond({
      "/control/traces": { items: [], can_view_workspace: false },
      "/control/quality": {
        days: 30,
        can_view_workspace: true,
        mode: "enforce",
        ask: {
          turns: 10,
          measured_turns: 10,
          violation_turns: 3,
          no_citation_turns: 2,
          fabricated_turns: 1,
          repair_attempted: 3,
          repaired: 2,
          fallback: 1,
        },
        structured: {
          calls: 8,
          measured_calls: 8,
          fence_stripped: 4,
          json_invalid: 1,
          schema_invalid: 0,
          semantic_invalid: 2,
          missing_content: 3,
          exhausted: 1,
        },
        evidence: { pages_total: 6, pages_with_evidence: 5 },
      },
    });
    const user = userEvent.setup();

    render(<ControlRoom workspaceId="ws" />);
    await waitFor(() => expect(apiFetch).toHaveBeenCalled());
    await user.click(screen.getByRole("tab", { name: "품질" }));

    const ask = await screen.findByRole("region", {
      name: "최근 30일 답변 인용 계약",
    });
    expect(ask).toHaveTextContent("2건 / 3건");
    expect(screen.getByText(/수리·근거 목록 대체 적용 중/)).toBeInTheDocument();
    expect(
      screen.getByRole("region", { name: "최근 30일 구조화 출력" }),
    ).toHaveTextContent("코드 펜스 제거");
    expect(
      screen.getByRole("region", { name: "최근 30일 구조화 출력" }),
    ).toHaveTextContent("본문 없는 응답3건");
    expect(
      screen.getByRole("region", { name: "위키 근거 청크" }),
    ).toHaveTextContent("5쪽 / 6쪽");
  });

  it("품질 탭에서 viewer에게는 수집 집계를 표시하지 않는다", async () => {
    respond({
      "/control/traces": { items: [], can_view_workspace: false },
      "/control/quality": {
        days: 30,
        can_view_workspace: false,
        mode: "enforce",
        ask: {
          turns: 1,
          measured_turns: 1,
          violation_turns: 0,
          no_citation_turns: 0,
          fabricated_turns: 0,
          repair_attempted: 0,
          repaired: 0,
          fallback: 0,
        },
        structured: null,
        evidence: null,
      },
    });
    const user = userEvent.setup();

    render(<ControlRoom workspaceId="ws" />);
    await waitFor(() => expect(apiFetch).toHaveBeenCalled());
    await user.click(screen.getByRole("tab", { name: "품질" }));

    await screen.findByRole("region", { name: "최근 30일 답변 인용 계약" });
    expect(
      screen.queryByRole("region", { name: "최근 30일 구조화 출력" }),
    ).toBeNull();
  });

  it("품질 탭은 집계할 데이터가 없으면 0을 꾸미지 않고 빈 상태를 표시한다", async () => {
    respond({
      "/control/traces": { items: [], can_view_workspace: false },
      "/control/quality": {
        days: 30,
        can_view_workspace: true,
        mode: "enforce",
        ask: {
          turns: 0,
          measured_turns: 0,
          violation_turns: 0,
          no_citation_turns: 0,
          fabricated_turns: 0,
          repair_attempted: 0,
          repaired: 0,
          fallback: 0,
        },
        structured: {
          calls: 0,
          measured_calls: 0,
          fence_stripped: 0,
          json_invalid: 0,
          schema_invalid: 0,
          semantic_invalid: 0,
          missing_content: 0,
          exhausted: 0,
        },
        // 위키가 있어도 기간 안에 턴과 호출이 없으면 빈 상태다.
        evidence: { pages_total: 12, pages_with_evidence: 12 },
      },
    });
    const user = userEvent.setup();

    render(<ControlRoom workspaceId="ws" />);
    await waitFor(() => expect(apiFetch).toHaveBeenCalled());
    await user.click(screen.getByRole("tab", { name: "품질" }));

    expect(
      await screen.findByText(/집계할 답변과 수집 호출이 없습니다/),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("region", { name: "최근 30일 답변 인용 계약" }),
    ).toBeNull();
  });

  function qualitySnapshot(
    ask: { turns: number; measured_turns: number },
    structured: { calls: number; measured_calls: number } | null,
  ) {
    return {
      days: 30,
      can_view_workspace: structured !== null,
      mode: "enforce",
      ask: {
        ...ask,
        violation_turns: 0,
        no_citation_turns: 0,
        fabricated_turns: 0,
        repair_attempted: 0,
        repaired: 0,
        fallback: 0,
      },
      structured: structured && {
        ...structured,
        fence_stripped: 0,
        json_invalid: 0,
        schema_invalid: 0,
        semantic_invalid: 0,
        missing_content: 0,
        exhausted: 0,
      },
      evidence: structured && { pages_total: 30, pages_with_evidence: 30 },
    };
  }

  async function openQuality(snapshot: unknown) {
    respond({
      "/control/traces": { items: [], can_view_workspace: false },
      "/control/quality": snapshot,
    });
    const user = userEvent.setup();
    render(<ControlRoom workspaceId="ws" />);
    await waitFor(() => expect(apiFetch).toHaveBeenCalled());
    await user.click(screen.getByRole("tab", { name: "품질" }));
    return screen.findByRole("region", { name: "최근 30일 답변 인용 계약" });
  }

  it("품질 탭은 측정 건수를 전체 건수와 함께 표시한다", async () => {
    const ask = await openQuality(
      qualitySnapshot(
        { turns: 6, measured_turns: 4 },
        { calls: 2, measured_calls: 1 },
      ),
    );

    expect(ask).toHaveTextContent("답변 턴 (측정 / 전체)");
    expect(ask).toHaveTextContent("4건 / 6건");
    expect(ask).toHaveTextContent("계약 위반 턴");
    const structured = screen.getByRole("region", {
      name: "최근 30일 구조화 출력",
    });
    expect(structured).toHaveTextContent("구조화 호출 (측정 / 전체)");
    expect(structured).toHaveTextContent("1건 / 2건");
    expect(structured).toHaveTextContent("JSON 오류");
    expect(screen.queryByText(/측정 기록 없음/)).toBeNull();
  });

  it("품질 탭은 측정 기록이 없는 경로의 지표를 0건으로 표시하지 않는다", async () => {
    const ask = await openQuality(
      qualitySnapshot(
        { turns: 2, measured_turns: 0 },
        { calls: 1, measured_calls: 0 },
      ),
    );

    expect(ask).toHaveTextContent("0건 / 2건");
    expect(ask).toHaveTextContent("측정 기록 없음");
    expect(ask).not.toHaveTextContent("계약 위반 턴");
    const structured = screen.getByRole("region", {
      name: "최근 30일 구조화 출력",
    });
    expect(structured).toHaveTextContent("0건 / 1건");
    expect(structured).toHaveTextContent("측정 기록 없음");
    expect(structured).not.toHaveTextContent("JSON 오류");
  });

  it("품질 탭은 한 경로에 데이터가 없으면 그 경로의 0건 지표를 숨긴다", async () => {
    const ask = await openQuality(
      qualitySnapshot(
        { turns: 0, measured_turns: 0 },
        { calls: 1, measured_calls: 1 },
      ),
    );

    expect(ask).toHaveTextContent("이 기간의 답변이 없습니다");
    expect(ask).not.toHaveTextContent("계약 위반 턴");
    expect(
      screen.getByRole("region", { name: "최근 30일 구조화 출력" }),
    ).toHaveTextContent("JSON 오류");
  });

  it("품질 탭은 측정 건수가 없는 이전 API 응답도 측정 기록 없음으로 표시한다", async () => {
    const snapshot = qualitySnapshot(
      { turns: 2, measured_turns: 0 },
      { calls: 1, measured_calls: 0 },
    );
    const ask: Record<string, unknown> = { ...snapshot.ask };
    delete ask.measured_turns;
    const structured: Record<string, unknown> = { ...snapshot.structured };
    delete structured.measured_calls;
    const region = await openQuality({ ...snapshot, ask, structured });

    expect(region).toHaveTextContent("0건 / 2건");
    expect(region).toHaveTextContent("측정 기록 없음");
    expect(region).not.toHaveTextContent("계약 위반 턴");
    expect(
      screen.getByRole("region", { name: "최근 30일 구조화 출력" }),
    ).not.toHaveTextContent("JSON 오류");
    expect(screen.queryByText(/undefined/)).toBeNull();
  });

  it("품질 탭에서 viewer도 본인 답변의 측정 기록 없음을 본다", async () => {
    const ask = await openQuality(
      qualitySnapshot({ turns: 1, measured_turns: 0 }, null),
    );

    expect(ask).toHaveTextContent("측정 기록 없음");
    expect(
      screen.queryByRole("region", { name: "최근 30일 구조화 출력" }),
    ).toBeNull();
  });

  it("품질 탭은 지표 묶음별 집계 기준을 화면 텍스트로 표시한다", async () => {
    const ask = await openQuality(
      qualitySnapshot(
        { turns: 6, measured_turns: 4 },
        { calls: 2, measured_calls: 1 },
      ),
    );

    expect(ask).toHaveTextContent("최근 30일 · 측정된 답변 기준");
    expect(
      screen.getByRole("region", { name: "최근 30일 구조화 출력" }),
    ).toHaveTextContent("최근 30일 · 측정된 호출 기준");
    expect(
      screen.getByRole("region", { name: "위키 근거 청크" }),
    ).toHaveTextContent("기간과 무관한 전체 페이지 기준");
  });

  const RISK_BASE = {
    days: 30,
    write_mode: "enforce",
    policy_version: "llm-policy-v1",
    recorded_policy_versions: ["llm-policy-v1"],
    revisions: { low: 3, medium: 2, high: 1 },
    proposals: { pending: 1, approved_waiting: 2, applied: 4, rejected: 0 },
  };

  it("리스크 탭에서 editor는 대기 제안을 보고 승인한다", async () => {
    respond({
      "/control/traces": { items: [], can_view_workspace: true },
      "/control/ask-aggregate": {
        days: 30,
        turn_count: 0,
        resolved_count: 0,
        no_evidence_count: 0,
        error_count: 0,
        decision_counts: {},
        p50_total_ms: null,
        p95_total_ms: null,
        total_cost_micros: 0,
        incomplete_call_count: 0,
      },
      "/control/risk": {
        ...RISK_BASE,
        can_view_workspace: true,
        pending_proposals: [
          {
            id: "p-1",
            wiki_id: "w-1",
            risk_reason: "verified_page",
            slug: "slug",
            current_title: "현재 제목",
            current_content: "현재 본문 내용",
            proposed_title: "제안 제목",
            proposed_content: "제안 본문 내용",
            updated_at: "2026-11-03T00:00:00Z",
          },
        ],
      },
      "/wiki-proposals/p-1/approve": { id: "p-1", status: "approved" },
    });
    const baseRespond = apiFetch.getMockImplementation();
    let approved = false;
    apiFetch.mockImplementation(async (path: string, init?: unknown) => {
      if (path.endsWith("/approve")) approved = true;
      if (approved && path.endsWith("/control/risk")) {
        return {
          ...RISK_BASE,
          can_view_workspace: true,
          proposals: {
            pending: 0,
            approved_waiting: 1,
            applied: 4,
            rejected: 0,
          },
          pending_proposals: [],
        };
      }
      return baseRespond?.(path, init);
    });
    const user = userEvent.setup();

    render(<ControlRoom workspaceId="ws" />);
    await waitFor(() => expect(apiFetch).toHaveBeenCalled());
    await user.click(screen.getByRole("tab", { name: "리스크" }));

    const list = await screen.findByRole("region", {
      name: "승인 대기 위키 변경",
    });
    expect(list).toHaveTextContent("제안 제목");
    expect(list).toHaveTextContent("검증 완료 문서");
    expect(list).toHaveTextContent("제안 본문 내용");
    expect(
      screen.getByRole("region", { name: "최근 30일 위키 개정 위험 등급" }),
    ).toHaveTextContent("1건");
    expect(screen.getByText(/llm-policy-v1/)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "승인" }));

    await waitFor(() =>
      expect(apiFetch).toHaveBeenCalledWith(
        "/workspaces/ws/wiki-proposals/p-1/approve",
        { method: "POST" },
      ),
    );
    // 처리한 뒤 목록을 다시 읽어 제안이 사라지고 집계가 갱신된다.
    await waitFor(() =>
      expect(
        screen.queryByRole("region", { name: "승인 대기 위키 변경" }),
      ).toBeNull(),
    );
    expect(
      screen.getByText("승인을 기다리는 위키 변경이 없습니다."),
    ).toBeInTheDocument();
  });

  it("리스크 탭은 최근 기간 지표와 현재 상태 지표를 나눠 표시한다", async () => {
    respond({
      "/control/traces": { items: [], can_view_workspace: false },
      "/control/risk": {
        ...RISK_BASE,
        can_view_workspace: false,
        pending_proposals: [],
      },
    });
    const user = userEvent.setup();

    render(<ControlRoom workspaceId="ws" />);
    await waitFor(() => expect(apiFetch).toHaveBeenCalled());
    await user.click(screen.getByRole("tab", { name: "리스크" }));

    const recent = await screen.findByRole("region", {
      name: "최근 30일 위키 개정 위험 등급",
    });
    expect(recent).toHaveTextContent("최근 30일 기준");
    expect(recent).toHaveTextContent("개정 높음");
    expect(recent).toHaveTextContent("승인 반영");
    expect(recent).toHaveTextContent("거부");
    expect(recent).not.toHaveTextContent("승인 대기");
    const current = screen.getByRole("region", { name: "현재 승인 상태" });
    expect(current).toHaveTextContent("현재 상태 기준");
    expect(current).toHaveTextContent("승인 대기1건");
    expect(current).toHaveTextContent("승인 후 반영 중2건");
    expect(screen.queryByRole("button", { name: "승인" })).toBeNull();
  });

  it("리스크 탭에서 viewer에게는 집계만 표시하고 처리 버튼이 없다", async () => {
    respond({
      "/control/traces": { items: [], can_view_workspace: false },
      "/control/risk": {
        ...RISK_BASE,
        recorded_policy_versions: [],
        can_view_workspace: false,
        pending_proposals: [],
      },
    });
    const user = userEvent.setup();

    render(<ControlRoom workspaceId="ws" />);
    await waitFor(() => expect(apiFetch).toHaveBeenCalled());
    await user.click(screen.getByRole("tab", { name: "리스크" }));

    await screen.findByRole("region", {
      name: "최근 30일 위키 개정 위험 등급",
    });
    expect(screen.getByText(/집계만 표시합니다/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "승인" })).toBeNull();
  });
});

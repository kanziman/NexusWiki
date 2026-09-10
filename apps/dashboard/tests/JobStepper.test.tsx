import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const apiFetch = vi.fn();

vi.mock("@/lib/api-client", () => ({
  apiFetch: (...args: unknown[]) => apiFetch(...args),
}));

import { JobStepper } from "@/components/JobStepper";

type JobRowOverrides = Partial<{
  id: string;
  type: string;
  step_label: string;
  chain_position: number | null;
  status: string;
  last_error: string | null;
}>;

function makeJob(overrides: JobRowOverrides = {}) {
  return {
    id: "job-1",
    type: "parse",
    step_label: "원문 파싱",
    chain_position: 1,
    chain_total: 5,
    status: "queued",
    attempts: 0,
    max_attempts: 5,
    run_after: "2026-08-12T00:00:00Z",
    last_error: null,
    cancel_requested_at: null,
    created_at: "2026-08-12T00:00:00Z",
    updated_at: "2026-08-12T00:00:00Z",
    ...overrides,
  };
}

describe("JobStepper", () => {
  beforeEach(() => {
    apiFetch.mockReset();
  });

  it("현재 단계와 완료 진행률만 compact summary로 렌더링한다", async () => {
    apiFetch.mockResolvedValue({
      jobs: [
        makeJob({
          id: "j-parse",
          type: "parse",
          step_label: "원문 파싱",
          chain_position: 1,
          status: "succeeded",
        }),
        makeJob({
          id: "j-compile",
          type: "compile",
          step_label: "위키 컴파일",
          chain_position: 2,
          status: "running",
        }),
        makeJob({
          id: "j-link",
          type: "link_sync",
          step_label: "링크 동기화",
          chain_position: 3,
          status: "queued",
        }),
        makeJob({
          id: "j-embed",
          type: "embed",
          step_label: "임베딩",
          chain_position: 4,
          status: "queued",
        }),
      ],
    });

    render(<JobStepper workspaceId="ws-1" rawSourceId="src-1" />);

    expect(
      await screen.findByText("위키 컴파일 처리 중 · 2/5단계 완료"),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("progressbar", { name: "처리 진행률 2/5단계 완료" }),
    ).toHaveAttribute("value", "2");
    expect(screen.queryByText("링크 동기화")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "취소" })).toBeInTheDocument();
  });

  it("모든 단계가 성공하면 완료 진행률만 표시하고 복구 행동을 숨긴다", async () => {
    apiFetch.mockResolvedValue({
      jobs: [
        makeJob({ id: "j-parse", type: "parse", status: "succeeded" }),
        makeJob({ id: "j-compile", type: "compile", status: "succeeded" }),
        makeJob({ id: "j-link", type: "link_sync", status: "succeeded" }),
        makeJob({ id: "j-embed", type: "embed", status: "succeeded" }),
      ],
    });

    render(<JobStepper workspaceId="ws-1" rawSourceId="src-1" />);

    expect(
      await screen.findByText("처리가 완료되었습니다 · 5/5단계 완료"),
    ).toBeInTheDocument();
    expect(screen.queryByRole("progressbar")).toBeNull();
    expect(screen.queryByRole("button", { name: "재시도" })).toBeNull();
    expect(screen.queryByRole("button", { name: "취소" })).toBeNull();
  });

  it("dead 상태 행에는 aria-label='재시도' 버튼이 있고, 클릭하면 재시도 엔드포인트를 호출한다", async () => {
    apiFetch.mockResolvedValue({
      jobs: [
        makeJob({
          id: "j-parse",
          type: "parse",
          step_label: "원문 파싱",
          chain_position: 1,
          status: "dead",
          last_error: "OCR 실패",
        }),
      ],
    });

    render(<JobStepper workspaceId="ws-1" rawSourceId="src-1" />);

    const retryButton = await screen.findByRole("button", { name: "재시도" });

    apiFetch.mockClear();
    apiFetch.mockResolvedValueOnce(undefined);
    fireEvent.click(retryButton);

    await waitFor(() =>
      expect(apiFetch).toHaveBeenCalledWith(
        "/workspaces/ws-1/jobs/j-parse/retry",
        { method: "POST" },
      ),
    );
  });

  it("자막 없음을 기계 토큰이 아니라 사람이 읽는 문구로 표시한다", async () => {
    apiFetch.mockResolvedValue({
      jobs: [
        makeJob({
          id: "j-parse",
          type: "parse",
          step_label: "원문 파싱",
          chain_position: 1,
          status: "dead",
          last_error: "no_transcript",
        }),
      ],
    });

    render(<JobStepper workspaceId="ws-1" rawSourceId="src-1" />);

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("사용할 수 있는 자막이 없습니다");
    expect(alert).not.toHaveTextContent("no_transcript");
    // ⚠️ 재시도해도 같은 자리에서 같은 이유로 끝난다. 버튼을 남기면 사용자를
    //    결과가 정해진 루프에 묶어두게 된다 — 대신 삭제를 안내한다.
    expect(screen.queryByRole("button", { name: "재시도" })).toBeNull();
    expect(alert).toHaveTextContent("삭제해 주세요");
  });

  it("공급자 일시 장애에는 재시도를 남긴다", async () => {
    apiFetch.mockResolvedValue({
      jobs: [
        makeJob({
          id: "j-parse",
          type: "parse",
          step_label: "원문 파싱",
          chain_position: 1,
          status: "dead",
          last_error: "provider_unavailable",
        }),
      ],
    });

    render(<JobStepper workspaceId="ws-1" rawSourceId="src-1" />);

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("일시적으로 연결하지 못했습니다");
    // 자막 없음과 달리 이쪽은 재시도로 풀린다.
    expect(screen.getByRole("button", { name: "재시도" })).toBeInTheDocument();
  });

  it("비공개·삭제된 영상을 자막 없음과 다른 문구로 구분한다", async () => {
    apiFetch.mockResolvedValue({
      jobs: [
        makeJob({
          id: "j-parse",
          type: "parse",
          step_label: "원문 파싱",
          chain_position: 1,
          status: "dead",
          last_error: "video_unavailable",
        }),
      ],
    });

    render(<JobStepper workspaceId="ws-1" rawSourceId="src-1" />);

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("비공개이거나 삭제되어");
    expect(screen.queryByRole("button", { name: "재시도" })).toBeNull();
  });

  it("실패하지 않은 작업에는 오류와 재시도 행동을 표시하지 않는다", async () => {
    apiFetch.mockResolvedValue({
      jobs: [makeJob({ status: "running" })],
    });

    render(<JobStepper workspaceId="ws-1" rawSourceId="src-1" />);

    await screen.findByText("원문 파싱 처리 중 · 1/5단계 완료");
    expect(screen.queryByRole("alert")).toBeNull();
    expect(screen.queryByRole("button", { name: "재시도" })).toBeNull();
  });

  it("취소 확인 다이얼로그는 정확한 문구를 표시한다", async () => {
    apiFetch.mockResolvedValue({
      jobs: [
        makeJob({
          id: "j-parse",
          type: "parse",
          step_label: "원문 파싱",
          chain_position: 1,
          status: "running",
        }),
      ],
    });

    const user = userEvent.setup();
    render(<JobStepper workspaceId="ws-1" rawSourceId="src-1" />);

    const cancelOpenButton = await screen.findByRole("button", {
      name: "취소",
    });
    await user.click(cancelOpenButton);

    const description = await screen.findByText(
      "진행 중인 작업을 취소하시겠습니까? 이미 사용된 비용은 환불되지 않습니다.",
    );
    expect(description).toHaveTextContent(
      "진행 중인 작업을 취소하시겠습니까? 이미 사용된 비용은 환불되지 않습니다.",
    );
  });

  it("크레딧 소진 실패 시 한국어 안내를 노출하고 충전 후 재시도할 수 있도록 버튼을 표시한다 (신규 토큰)", async () => {
    apiFetch.mockResolvedValue({
      jobs: [
        makeJob({
          id: "j-compile",
          type: "compile",
          step_label: "위키 컴파일",
          chain_position: 2,
          status: "dead",
          last_error:
            "provider_credit_exhausted provider=openrouter kind=chat_completion",
        }),
      ],
    });

    render(<JobStepper workspaceId="ws-1" rawSourceId="src-1" />);

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(
      "AI 크레딧이 소진되었습니다. 크레딧 충전 또는 API 키 확인 후 재시도해 주세요.",
    );
    expect(screen.getByRole("button", { name: "재시도" })).toBeInTheDocument();
  });

  it("기존 DB의 provider_error 402 에러 문자열도 크레딧 소진 안내로 매핑하고 재시도 버튼을 표시한다", async () => {
    apiFetch.mockResolvedValue({
      jobs: [
        makeJob({
          id: "j-compile",
          type: "compile",
          step_label: "위키 컴파일",
          chain_position: 2,
          status: "dead",
          last_error:
            "provider_error kind=chat_completion provider=openrouter status=402",
        }),
      ],
    });

    render(<JobStepper workspaceId="ws-1" rawSourceId="src-1" />);

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(
      "AI 크레딧이 소진되었습니다. 크레딧 충전 또는 API 키 확인 후 재시도해 주세요.",
    );
    expect(screen.getByRole("button", { name: "재시도" })).toBeInTheDocument();
  });

  it("upstream_error status=402는 AI 크레딧 소진으로 오인하지 않고 일반 실패 문구를 노출한다", async () => {
    apiFetch.mockResolvedValue({
      jobs: [
        makeJob({
          id: "j-parse",
          type: "parse",
          step_label: "원문 파싱",
          chain_position: 1,
          status: "dead",
          last_error: "upstream_error status=402",
        }),
      ],
    });

    render(<JobStepper workspaceId="ws-1" rawSourceId="src-1" />);

    const alert = await screen.findByRole("alert");
    expect(alert).not.toHaveTextContent("AI 크레딧이 소진되었습니다");
    expect(alert).toHaveTextContent("원문 파싱 단계에서 실패했습니다");
    expect(screen.getByRole("button", { name: "재시도" })).toBeInTheDocument();
  });
});

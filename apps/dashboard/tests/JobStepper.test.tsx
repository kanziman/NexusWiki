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

  it("5단계 라벨을 모두 렌더링하고 컴파일을 현재 단계로 강조한다", async () => {
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

    await screen.findByText("컴파일");
    for (const label of ["업로드", "파싱", "컴파일", "링크 동기화", "임베딩"]) {
      expect(screen.getByText(label)).toBeInTheDocument();
    }
    expect(screen.getByText("컴파일")).toHaveClass("text-primary");
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
});

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const apiFetch = vi.fn();

vi.mock("@/lib/api-client", () => ({
  apiFetch: (...args: unknown[]) => apiFetch(...args),
}));
vi.mock("@/components/MembersList", () => ({
  MembersList: () => <div>멤버 목록</div>,
}));
vi.mock("@/components/InviteForm", () => ({
  InviteForm: () => <div>멤버 초대 폼</div>,
}));

import { OperationsPanel } from "@/components/OperationsPanel";
import { SettingsMembersPanel } from "@/components/SettingsMembersPanel";

function snapshot(overrides: Partial<Record<string, unknown>> = {}) {
  return {
    budget: {
      cap_micros: 5_000_000,
      spent_micros: 1_250_000,
      remaining_micros: 3_750_000,
      month_start: "2026-08-01T00:00:00+00:00",
      truncated: false,
      authoritative: false,
    },
    pipeline: [
      {
        type: "parse",
        step_label: "원문 파싱",
        queued: 1,
        running: 0,
        dead: 0,
      },
      {
        type: "compile",
        step_label: "위키 컴파일",
        queued: 0,
        running: 1,
        dead: 0,
      },
      {
        type: "link_sync",
        step_label: "링크 동기화",
        queued: 0,
        running: 0,
        dead: 0,
      },
      { type: "embed", step_label: "임베딩", queued: 0, running: 0, dead: 2 },
      {
        type: "conflict_check",
        step_label: "지식 충돌 검사",
        queued: 0,
        running: 0,
        dead: 0,
      },
    ],
    observed_at: "2026-08-13T12:34:56.000Z",
    ...overrides,
  };
}

describe("OperationsPanel", () => {
  beforeEach(() => apiFetch.mockReset());

  it("initially renders neutral skeletons, then server-provided rows and local timestamp", async () => {
    let resolve!: (value: ReturnType<typeof snapshot>) => void;
    apiFetch.mockReturnValue(
      new Promise((done) => {
        resolve = done;
      }),
    );
    render(<OperationsPanel workspaceId="ws-1" />);
    expect(
      screen.getByLabelText("운영 현황을 불러오는 중"),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "운영 현황 새로고침" }),
    ).toBeDisabled();
    resolve(snapshot());
    expect(await screen.findByText("원문 파싱")).toBeInTheDocument();
    expect(apiFetch).toHaveBeenCalledTimes(1);
    expect(apiFetch).toHaveBeenCalledWith("/workspaces/ws-1/operations");
    expect(screen.getByText(/마지막 갱신:/)).toBeInTheDocument();
    expect(screen.getByText("실패한 작업 2건")).toBeInTheDocument();
  });

  it("renders cap-zero, empty, partial and unavailable state without job internals", async () => {
    apiFetch.mockResolvedValue(
      snapshot({
        budget: {
          cap_micros: 0,
          spent_micros: 0,
          remaining_micros: 0,
          month_start: "2026-08-01T00:00:00Z",
          truncated: true,
          authoritative: false,
        },
        pipeline: [
          {
            type: "parse",
            step_label: "매우 긴 서버 단계 라벨",
            queued: null,
            running: 0,
            dead: 0,
          },
        ],
      }),
    );
    render(<OperationsPanel workspaceId="ws-1" />);
    expect(
      await screen.findByText("예산이 설정되지 않았습니다."),
    ).toBeInTheDocument();
    expect(
      screen.getByText("이번 달 사용 기록이 없습니다."),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/표시할 수 있는 사용 기록이 많아/),
    ).toBeInTheDocument();
    expect(screen.getByText("집계 불가")).toBeInTheDocument();
    expect(screen.getByTitle("매우 긴 서버 단계 라벨")).toHaveClass("truncate");
  });

  it("retains the successful snapshot and uses contracted error copy when manual refresh fails", async () => {
    apiFetch.mockResolvedValueOnce(
      snapshot({
        budget: {
          cap_micros: 999_999_999_999_999,
          spent_micros: 500_000_000_000_000,
          remaining_micros: 499_999_999_999_999,
          month_start: "2026-08-01T00:00:00Z",
          truncated: false,
          authoritative: false,
        },
      }),
    );
    const user = userEvent.setup();
    render(<OperationsPanel workspaceId="ws-1" />);
    await screen.findByText("원문 파싱");
    let rejectRefresh!: (error: Error) => void;
    apiFetch.mockReturnValueOnce(
      new Promise((_, reject) => {
        rejectRefresh = reject;
      }),
    );
    await user.click(
      screen.getByRole("button", { name: "운영 현황 새로고침" }),
    );
    expect(
      screen.getByRole("button", { name: "운영 현황 새로고침" }),
    ).toHaveAttribute("aria-busy", "true");
    rejectRefresh(new Error("provider=private raw failure"));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "운영 현황을 불러오지 못했습니다. 운영 현황 새로고침을 시도해주세요.",
    );
    expect(screen.getByText("원문 파싱")).toBeInTheDocument();
    expect(
      screen.queryByText("provider=private raw failure"),
    ).not.toBeInTheDocument();
  });

  it("keeps all five zero-count rows and explains an empty pipeline", async () => {
    apiFetch.mockResolvedValue(
      snapshot({
        pipeline: snapshot().pipeline.map((row) => ({
          ...row,
          queued: 0,
          running: 0,
          dead: 0,
        })),
      }),
    );
    render(<OperationsPanel workspaceId="ws-1" />);
    expect(
      await screen.findByText("처리 중이거나 대기 중인 작업이 없습니다."),
    ).toBeInTheDocument();
    expect(screen.getAllByText("0건")).toHaveLength(15);
  });

  it("only requests operations after an owner opens its keyboard-operable tab; viewers never request or render it", async () => {
    const user = userEvent.setup();
    apiFetch.mockResolvedValue(snapshot());
    const { rerender } = render(
      <SettingsMembersPanel
        workspaceId="ws-1"
        currentUserId="viewer"
        currentRole="viewer"
      />,
    );
    expect(
      screen.queryByRole("tab", { name: "운영 현황" }),
    ).not.toBeInTheDocument();
    expect(apiFetch).not.toHaveBeenCalled();

    rerender(
      <SettingsMembersPanel
        workspaceId="ws-1"
        currentUserId="owner"
        currentRole="owner"
      />,
    );
    const operationsTab = screen.getByRole("tab", { name: "운영 현황" });
    fireEvent.keyDown(screen.getByRole("tab", { name: "멤버" }), {
      key: "ArrowRight",
    });
    await waitFor(() =>
      expect(operationsTab).toHaveAttribute("aria-selected", "true"),
    );
    expect(await screen.findByText("원문 파싱")).toBeInTheDocument();
    expect(apiFetch).toHaveBeenCalledTimes(1);
    await user.click(screen.getByRole("tab", { name: "멤버" }));
    expect(screen.getByRole("tabpanel", { name: "멤버" })).toBeInTheDocument();
  });
});

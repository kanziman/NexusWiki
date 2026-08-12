import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

// MembersList가 0014의 두 RPC/direct-write 표면만 통해 데이터를 읽고 쓰도록
// 강제한다 — lib/supabase/client.ts를 모킹해 실제 네트워크 호출 없이 rpc/from
// 호출 인자만 관찰한다 (LoginForm.test.tsx와 같은 패턴).
const rpc = vi.fn();
// 06-REVIEW.md WR-03 fix: handleConfirmRemove가 이제 .match() 뒤에 .select()를
// 체이닝해 삭제된 행 수를 확인한다 — 목도 그 체인 모양을 그대로 흉내낸다.
const select = vi.fn();
const match = vi.fn(() => ({ select }));
const del = vi.fn(() => ({ match }));
const from = vi.fn(() => ({ delete: del }));

vi.mock("@/lib/supabase/client", () => ({
  createClient: () => ({ rpc, from }),
}));

import { MembersList } from "@/components/MembersList";

const rows = [
  {
    user_id: "owner-1",
    email: "owner@example.com",
    role: "owner",
    created_at: "2026-01-01T00:00:00Z",
  },
  {
    user_id: "editor-1",
    email: "editor@example.com",
    role: "editor",
    created_at: "2026-01-02T00:00:00Z",
  },
];

describe("MembersList", () => {
  beforeEach(() => {
    rpc.mockReset();
    match.mockClear();
    select.mockReset();
    del.mockClear();
    from.mockClear();
    select.mockResolvedValue({
      data: [{ user_id: "editor-1" }],
      error: null,
    });
  });

  it("workspace_members_list RPC가 반환한 두 멤버의 이메일과 역할 배지를 렌더링한다", async () => {
    rpc.mockResolvedValue({ data: rows, error: null });

    render(<MembersList workspaceId="ws-1" currentUserId="owner-1" />);

    expect(await screen.findByText("owner@example.com")).toBeInTheDocument();
    expect(screen.getByText("editor@example.com")).toBeInTheDocument();
    expect(screen.getByText("소유자")).toBeInTheDocument();
    expect(screen.getByText("편집자")).toBeInTheDocument();
    expect(rpc).toHaveBeenCalledWith("workspace_members_list", {
      p_workspace_id: "ws-1",
    });
  });

  it("초기 조회 동안 스켈레톤 상태를 보여준다", () => {
    rpc.mockReturnValue(new Promise(() => {})); // never resolves during this render

    render(<MembersList workspaceId="ws-1" currentUserId="owner-1" />);

    expect(screen.getByTestId("members-list-skeleton")).toBeInTheDocument();
  });

  it("owner가 다른 멤버를 제거 확인 후 정확한 {workspace_id, user_id} 쌍으로 delete().match()를 호출한다", async () => {
    rpc.mockResolvedValue({ data: rows, error: null });
    const user = userEvent.setup();

    render(<MembersList workspaceId="ws-1" currentUserId="owner-1" />);

    await screen.findByText("editor@example.com");

    await user.click(
      screen.getByRole("button", { name: "제거: editor@example.com" }),
    );

    await screen.findByText(
      "제거: editor@example.com님을 이 워크스페이스에서 제거하시겠습니까? 소유한 콘텐츠는 유지되지만 접근 권한이 즉시 사라집니다.",
    );

    await user.click(screen.getByRole("button", { name: "제거" }));

    await waitFor(() =>
      expect(match).toHaveBeenCalledWith({
        workspace_id: "ws-1",
        user_id: "editor-1",
      }),
    );
    expect(from).toHaveBeenCalledWith("workspace_members");
    expect(select).toHaveBeenCalled();
    expect(screen.queryByText("editor@example.com")).not.toBeInTheDocument();
  });

  it("06-REVIEW.md WR-03: RLS에 막혀 0행이 삭제되면(error:null, data:[]) 에러 배너를 보여주고 멤버를 목록에 남긴다", async () => {
    rpc.mockResolvedValue({ data: rows, error: null });
    select.mockResolvedValue({ data: [], error: null });
    const user = userEvent.setup();

    render(<MembersList workspaceId="ws-1" currentUserId="owner-1" />);

    await screen.findByText("editor@example.com");

    await user.click(
      screen.getByRole("button", { name: "제거: editor@example.com" }),
    );

    await screen.findByText(
      "제거: editor@example.com님을 이 워크스페이스에서 제거하시겠습니까? 소유한 콘텐츠는 유지되지만 접근 권한이 즉시 사라집니다.",
    );

    await user.click(screen.getByRole("button", { name: "제거" }));

    await screen.findByText("멤버를 제거하지 못했습니다.");
    // 0행 삭제는 성공이 아니다 — 로컬 state에서 낙관적으로 지워지면 안 된다.
    expect(screen.getByText("editor@example.com")).toBeInTheDocument();
  });

  it("owner 자신의 행에는 제거 버튼을 그리지 않는다", async () => {
    rpc.mockResolvedValue({ data: rows, error: null });

    render(<MembersList workspaceId="ws-1" currentUserId="owner-1" />);

    await screen.findByText("owner@example.com");

    expect(
      screen.queryByRole("button", { name: "제거: owner@example.com" }),
    ).not.toBeInTheDocument();
  });

  it("owner가 아니면 제거 버튼을 아무 행에도 그리지 않는다", async () => {
    rpc.mockResolvedValue({ data: rows, error: null });

    render(<MembersList workspaceId="ws-1" currentUserId="editor-1" />);

    await screen.findByText("editor@example.com");

    expect(
      screen.queryByRole("button", { name: /제거:/ }),
    ).not.toBeInTheDocument();
  });
});

import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

// InviteForm이 0014의 invite_workspace_member RPC만 통해 초대를 보내도록
// 강제한다 — lib/supabase/client.ts를 모킹해 실제 네트워크 호출 없이 rpc 호출
// 인자와 반환값(성공/NW409/NW404) 분기만 검증한다 (LoginForm.test.tsx와 같은 패턴).
const rpc = vi.fn();

vi.mock("@/lib/supabase/client", () => ({
  createClient: () => ({ rpc }),
}));

import { InviteForm } from "@/components/InviteForm";

describe("InviteForm", () => {
  beforeEach(() => {
    rpc.mockReset();
  });

  it("이메일 형식이 올바르지 않으면 제출 버튼이 비활성화된다", () => {
    render(<InviteForm workspaceId="ws-1" />);

    fireEvent.change(screen.getByLabelText("이메일"), {
      target: { value: "not-an-email" },
    });

    expect(screen.getByRole("button", { name: "초대 보내기" })).toBeDisabled();
  });

  it("역할을 건드리지 않으면 기본값이 뷰어이고, 유효한 이메일이면 제출이 활성화된다", () => {
    render(<InviteForm workspaceId="ws-1" />);

    fireEvent.change(screen.getByLabelText("이메일"), {
      target: { value: "invite@example.com" },
    });

    // Radix Select는 접근성용 숨김 <select><option>도 함께 렌더링하므로,
    // 화면에 보이는 combobox 트리거로 범위를 좁혀 검사한다.
    expect(
      within(screen.getByRole("combobox")).getByText("뷰어"),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "초대 보내기" }),
    ).not.toBeDisabled();
  });

  it("NW409 에러면 중복 멤버 문구를 정확히 렌더링하고 이메일 입력을 비우지 않는다", async () => {
    rpc.mockResolvedValue({
      data: null,
      error: { code: "NW409", message: "duplicate member" },
    });

    render(<InviteForm workspaceId="ws-1" />);

    const emailInput = screen.getByLabelText("이메일") as HTMLInputElement;
    fireEvent.change(emailInput, { target: { value: "dup@example.com" } });
    fireEvent.click(screen.getByRole("button", { name: "초대 보내기" }));

    await screen.findByText("이미 워크스페이스 멤버입니다.");
    expect(emailInput.value).toBe("dup@example.com");
  });

  it("NW404 에러면 미가입 사용자 안내 문구를 렌더링한다", async () => {
    rpc.mockResolvedValue({
      data: null,
      error: { code: "NW404", message: "not found" },
    });

    render(<InviteForm workspaceId="ws-1" />);

    fireEvent.change(screen.getByLabelText("이메일"), {
      target: { value: "ghost@example.com" },
    });
    fireEvent.click(screen.getByRole("button", { name: "초대 보내기" }));

    await screen.findByText(
      "가입된 사용자를 찾을 수 없습니다 — 초대 대상이 먼저 NexusWiki 계정을 만들어야 합니다.",
    );
  });

  it("성공하면 onInvited를 호출하고 이메일 입력을 비운다", async () => {
    rpc.mockResolvedValue({
      data: [{ user_id: "u1", email: "ok@example.com", role: "viewer" }],
      error: null,
    });
    const onInvited = vi.fn();

    render(<InviteForm workspaceId="ws-1" onInvited={onInvited} />);

    const emailInput = screen.getByLabelText("이메일") as HTMLInputElement;
    fireEvent.change(emailInput, { target: { value: "ok@example.com" } });
    fireEvent.click(screen.getByRole("button", { name: "초대 보내기" }));

    await waitFor(() => expect(onInvited).toHaveBeenCalled());
    expect(emailInput.value).toBe("");
    expect(rpc).toHaveBeenCalledWith("invite_workspace_member", {
      p_workspace_id: "ws-1",
      p_email: "ok@example.com",
      p_role: "viewer",
    });
  });

  it("isPersonal이 true면 안내 노트를 렌더링하고 입력 및 버튼이 비활성화된다", () => {
    render(<InviteForm workspaceId="ws-1" isPersonal={true} />);

    expect(
      screen.getByText("개인 워크스페이스는 멤버 초대가 비활성화되어 있습니다"),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("이메일")).toBeDisabled();
    expect(screen.getByRole("button", { name: "초대 보내기" })).toBeDisabled();
  });
});

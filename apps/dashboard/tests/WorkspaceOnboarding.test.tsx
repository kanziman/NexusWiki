import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const push = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));

import { WorkspaceOnboarding } from "@/components/WorkspaceOnboarding";

describe("WorkspaceOnboarding", () => {
  beforeEach(() => {
    push.mockReset();
  });

  it("빈 이름은 제출할 수 없다", () => {
    render(<WorkspaceOnboarding createWorkspace={vi.fn()} />);

    expect(
      screen.getByRole("button", { name: "워크스페이스 만들기" }),
    ).toBeDisabled();
  });

  it("유효한 이름으로 생성되면 UUID 기반 workspace 경로로 이동한다", async () => {
    const user = userEvent.setup();
    const createWorkspace = vi.fn().mockResolvedValue({ workspaceId: "ws-1" });
    render(<WorkspaceOnboarding createWorkspace={createWorkspace} />);

    await user.type(screen.getByLabelText("워크스페이스 이름"), "나의 위키");
    await user.click(
      screen.getByRole("button", { name: "워크스페이스 만들기" }),
    );

    expect(createWorkspace).toHaveBeenCalledWith("나의 위키");
    expect(push).toHaveBeenCalledWith("/w/ws-1");
  });

  it("서버 입력 오류를 표시한다", async () => {
    const user = userEvent.setup();
    render(
      <WorkspaceOnboarding
        createWorkspace={vi
          .fn()
          .mockResolvedValue({ error: "이름은 1~100자여야 합니다." })}
      />,
    );

    await user.type(screen.getByLabelText("워크스페이스 이름"), "나의 위키");
    await user.click(
      screen.getByRole("button", { name: "워크스페이스 만들기" }),
    );

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "이름은 1~100자여야 합니다.",
    );
  });
});

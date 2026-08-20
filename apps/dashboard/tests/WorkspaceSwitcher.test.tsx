import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

// D-03: onSelect가 workspacePath()를 재구현하지 않고 그대로 호출하는지 검증하려면
// next/navigation의 useRouter를 모킹해 push 호출 인자를 관찰해야 한다.
const push = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
}));

const createPersonalWorkspace = vi.fn();
vi.mock("@/app/onboarding-actions", () => ({
  createPersonalWorkspace: (...args: unknown[]) =>
    createPersonalWorkspace(...args),
}));

import { WorkspaceSwitcher } from "@/components/WorkspaceSwitcher";

const workspaces: { id: string; name: string; kind: "personal" | "team" }[] = [
  { id: "ws-1", name: "워크스페이스 하나", kind: "personal" },
  { id: "ws-2", name: "워크스페이스 둘", kind: "team" },
];

describe("WorkspaceSwitcher", () => {
  beforeEach(() => {
    push.mockReset();
    createPersonalWorkspace.mockReset();
  });

  it("스위처 버튼에 현재 워크스페이스 이름이 렌더링된다", () => {
    render(
      <WorkspaceSwitcher workspaces={workspaces} currentWorkspaceId="ws-1" />,
    );

    expect(
      screen.getByRole("button", { name: /워크스페이스 하나/ }),
    ).toBeInTheDocument();
  });

  it('현재 워크스페이스 항목만 data-active="true"를 갖는다', async () => {
    const user = userEvent.setup();
    render(
      <WorkspaceSwitcher workspaces={workspaces} currentWorkspaceId="ws-1" />,
    );

    await user.click(screen.getByRole("button", { name: /워크스페이스 하나/ }));

    const activeItem = await screen.findByRole("menuitem", {
      name: /워크스페이스 하나/,
    });
    const inactiveItem = await screen.findByRole("menuitem", {
      name: /워크스페이스 둘/,
    });

    expect(activeItem).toHaveAttribute("data-active", "true");
    expect(inactiveItem).not.toHaveAttribute("data-active");
  });

  it("활성이 아닌 워크스페이스를 선택하면 workspacePath()로 이동한다", async () => {
    const user = userEvent.setup();
    render(
      <WorkspaceSwitcher workspaces={workspaces} currentWorkspaceId="ws-1" />,
    );

    await user.click(screen.getByRole("button", { name: /워크스페이스 하나/ }));

    const otherItem = await screen.findByRole("menuitem", {
      name: /워크스페이스 둘/,
    });
    await user.click(otherItem);

    expect(push).toHaveBeenCalledWith("/w/ws-2");
  });

  it("현재 워크스페이스 항목을 선택해도 push를 호출하지 않는다", async () => {
    const user = userEvent.setup();
    render(
      <WorkspaceSwitcher workspaces={workspaces} currentWorkspaceId="ws-1" />,
    );

    await user.click(screen.getByRole("button", { name: /워크스페이스 하나/ }));

    const activeItem = await screen.findByRole("menuitem", {
      name: /워크스페이스 하나/,
    });
    await user.click(activeItem);

    expect(push).not.toHaveBeenCalled();
  });

  it("소속 워크스페이스가 3개 미만이면 생성 진입점을 보여준다", async () => {
    const user = userEvent.setup();
    render(
      <WorkspaceSwitcher workspaces={workspaces} currentWorkspaceId="ws-1" />,
    );

    await user.click(screen.getByRole("button", { name: /워크스페이스 하나/ }));

    expect(
      await screen.findByRole("button", { name: "새 워크스페이스 생성" }),
    ).toBeInTheDocument();
  });

  it("소속 워크스페이스가 3개면 생성 진입점을 보여주지 않는다", async () => {
    const user = userEvent.setup();
    const threeWorkspaces: typeof workspaces = [
      ...workspaces,
      { id: "ws-3", name: "워크스페이스 셋", kind: "personal" },
    ];
    render(
      <WorkspaceSwitcher
        workspaces={threeWorkspaces}
        currentWorkspaceId="ws-1"
      />,
    );

    await user.click(screen.getByRole("button", { name: /워크스페이스 하나/ }));

    expect(
      screen.queryByRole("button", { name: "새 워크스페이스 생성" }),
    ).not.toBeInTheDocument();
  });

  it("생성 진입점을 누르면 드롭다운을 닫지 않고 인라인 입력 폼으로 바뀐다", async () => {
    const user = userEvent.setup();
    render(
      <WorkspaceSwitcher workspaces={workspaces} currentWorkspaceId="ws-1" />,
    );

    await user.click(screen.getByRole("button", { name: /워크스페이스 하나/ }));
    await user.click(
      await screen.findByRole("button", { name: "새 워크스페이스 생성" }),
    );

    // 드롭다운이 여전히 열려 있다 — 기존 워크스페이스 목록이 계속 보인다.
    expect(
      screen.getByRole("menuitem", { name: /워크스페이스 하나/ }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("textbox", { name: "새 워크스페이스 이름" }),
    ).toBeInTheDocument();
  });

  it("생성 진입점은 키보드(Enter)로도 인라인 폼을 연다", async () => {
    const user = userEvent.setup();
    render(
      <WorkspaceSwitcher workspaces={workspaces} currentWorkspaceId="ws-1" />,
    );

    await user.click(screen.getByRole("button", { name: /워크스페이스 하나/ }));
    const entry = await screen.findByRole("button", {
      name: "새 워크스페이스 생성",
    });
    entry.focus();
    await user.keyboard("{Enter}");

    expect(
      screen.getByRole("textbox", { name: "새 워크스페이스 이름" }),
    ).toBeInTheDocument();
  });

  it("인라인 폼 제출이 createPersonalWorkspace를 호출하고 성공하면 새 워크스페이스로 이동한다", async () => {
    createPersonalWorkspace.mockResolvedValue({ workspaceId: "ws-new" });
    const user = userEvent.setup();
    render(
      <WorkspaceSwitcher workspaces={workspaces} currentWorkspaceId="ws-1" />,
    );

    await user.click(screen.getByRole("button", { name: /워크스페이스 하나/ }));
    await user.click(
      await screen.findByRole("button", { name: "새 워크스페이스 생성" }),
    );
    await user.type(
      screen.getByRole("textbox", { name: "새 워크스페이스 이름" }),
      "새 워크스페이스",
    );
    await user.click(screen.getByRole("button", { name: "생성" }));

    expect(createPersonalWorkspace).toHaveBeenCalledWith("새 워크스페이스");
    await waitFor(() => expect(push).toHaveBeenCalledWith("/w/ws-new"));
  });

  it("인라인 폼 제출이 실패하면(상한 도달 등) 폼 안에 오류를 보여주고 입력값을 유지한다", async () => {
    createPersonalWorkspace.mockResolvedValue({
      error: "워크스페이스는 최대 3개까지 만들 수 있습니다.",
    });
    const user = userEvent.setup();
    render(
      <WorkspaceSwitcher workspaces={workspaces} currentWorkspaceId="ws-1" />,
    );

    await user.click(screen.getByRole("button", { name: /워크스페이스 하나/ }));
    await user.click(
      await screen.findByRole("button", { name: "새 워크스페이스 생성" }),
    );
    const input = screen.getByRole("textbox", { name: "새 워크스페이스 이름" });
    await user.type(input, "새 워크스페이스");
    await user.click(screen.getByRole("button", { name: "생성" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "워크스페이스는 최대 3개까지 만들 수 있습니다.",
    );
    expect(input).toHaveValue("새 워크스페이스");
    expect(push).not.toHaveBeenCalled();
  });

  it("취소하면 입력값을 버리고 진입점으로 되돌리며, 워크스페이스를 생성하지 않는다", async () => {
    const user = userEvent.setup();
    render(
      <WorkspaceSwitcher workspaces={workspaces} currentWorkspaceId="ws-1" />,
    );

    await user.click(screen.getByRole("button", { name: /워크스페이스 하나/ }));
    await user.click(
      await screen.findByRole("button", { name: "새 워크스페이스 생성" }),
    );
    await user.type(
      screen.getByRole("textbox", { name: "새 워크스페이스 이름" }),
      "버릴 이름",
    );
    await user.click(screen.getByRole("button", { name: "취소" }));

    expect(
      screen.getByRole("button", { name: "새 워크스페이스 생성" }),
    ).toBeInTheDocument();
    expect(createPersonalWorkspace).not.toHaveBeenCalled();

    // 다시 열어도 이전 입력이 남아있지 않다.
    await user.click(
      screen.getByRole("button", { name: "새 워크스페이스 생성" }),
    );
    expect(
      screen.getByRole("textbox", { name: "새 워크스페이스 이름" }),
    ).toHaveValue("");
  });

  it("드롭다운을 닫으면 인라인 폼 상태가 리셋된다", async () => {
    const user = userEvent.setup();
    render(
      <WorkspaceSwitcher workspaces={workspaces} currentWorkspaceId="ws-1" />,
    );

    const trigger = screen.getByRole("button", { name: /워크스페이스 하나/ });
    await user.click(trigger);
    await user.click(
      await screen.findByRole("button", { name: "새 워크스페이스 생성" }),
    );
    await user.type(
      screen.getByRole("textbox", { name: "새 워크스페이스 이름" }),
      "버릴 이름",
    );

    // Radix DismissableLayer가 document 레벨에서 듣는 Escape로 드롭다운
    // 자체를 닫는다(onOpenChange(false) 경로) — input의 자체 Escape
    // 핸들러(stopPropagation)를 우회하려고 input이 아니라 document에 직접
    // 이벤트를 쏜다.
    fireEvent.keyDown(document, { key: "Escape" });
    await waitFor(() =>
      expect(
        screen.queryByRole("textbox", { name: "새 워크스페이스 이름" }),
      ).not.toBeInTheDocument(),
    );

    await user.click(trigger);
    await user.click(
      await screen.findByRole("button", { name: "새 워크스페이스 생성" }),
    );
    expect(
      screen.getByRole("textbox", { name: "새 워크스페이스 이름" }),
    ).toHaveValue("");
  });
});

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

// D-03: onSelect가 workspacePath()를 재구현하지 않고 그대로 호출하는지 검증하려면
// next/navigation의 useRouter를 모킹해 push 호출 인자를 관찰해야 한다.
const push = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
}));

import { WorkspaceSwitcher } from "@/components/WorkspaceSwitcher";

const workspaces = [
  { id: "ws-1", name: "워크스페이스 하나" },
  { id: "ws-2", name: "워크스페이스 둘" },
];

describe("WorkspaceSwitcher", () => {
  beforeEach(() => {
    push.mockReset();
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

  it("소속 워크스페이스가 3개 미만이면 /w/new로 가는 생성 링크를 보여준다", async () => {
    const user = userEvent.setup();
    render(
      <WorkspaceSwitcher workspaces={workspaces} currentWorkspaceId="ws-1" />,
    );

    await user.click(screen.getByRole("button", { name: /워크스페이스 하나/ }));

    const createLink = await screen.findByRole("menuitem", {
      name: /새 워크스페이스 생성/,
    });
    expect(createLink).toHaveAttribute("href", "/w/new");
  });

  it("소속 워크스페이스가 3개면 생성 링크를 보여주지 않는다", async () => {
    const user = userEvent.setup();
    const threeWorkspaces = [
      ...workspaces,
      { id: "ws-3", name: "워크스페이스 셋" },
    ];
    render(
      <WorkspaceSwitcher
        workspaces={threeWorkspaces}
        currentWorkspaceId="ws-1"
      />,
    );

    await user.click(screen.getByRole("button", { name: /워크스페이스 하나/ }));

    expect(
      screen.queryByRole("menuitem", { name: /새 워크스페이스 생성/ }),
    ).not.toBeInTheDocument();
  });
});

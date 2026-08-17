import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

const mockUsePathname = vi.hoisted(() => vi.fn(() => "/w/ws-1"));
const mockSearchParamsGet = vi.hoisted(() => vi.fn(() => null));

vi.mock("next/navigation", () => ({
  usePathname: mockUsePathname,
  useSearchParams: () => ({
    get: mockSearchParamsGet,
  }),
}));

vi.mock("@/components/WorkspaceSwitcher", () => ({
  WorkspaceSwitcher: ({ workspaces }: { workspaces: { name: string }[] }) => (
    <div data-testid="workspace-switcher">{workspaces[0]?.name}</div>
  ),
}));

import { WorkspaceSidebar } from "@/components/WorkspaceSidebar";

describe("WorkspaceSidebar", () => {
  const defaultProps = {
    currentWorkspaceId: "ws-1",
    workspaces: [{ id: "ws-1", name: "테스트 워크스페이스" }],
    accountEmail: "developer@nexuswiki.com",
  };

  it("renders main navigation items, categories, and user profile", () => {
    render(<WorkspaceSidebar {...defaultProps} />);

    expect(screen.getByText("테스트 워크스페이스")).toBeInTheDocument();

    expect(
      screen.getByRole("link", { name: /홈 대시보드/ }),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /원문 소스/ })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /질문하기/ })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /위키 문서/ })).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: /미완성 백로그/ }),
    ).toBeInTheDocument();

    expect(screen.getByRole("link", { name: "개념" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "엔티티" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "가이드" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "맵" })).toBeInTheDocument();

    expect(
      screen.getByRole("link", { name: /팀원 & 역할 관리/ }),
    ).toBeInTheDocument();

    // Profile initial and email
    expect(screen.getByText("D")).toBeInTheDocument();
    expect(screen.getByText("developer")).toBeInTheDocument();
    expect(screen.getByText("developer@nexuswiki.com")).toBeInTheDocument();
  });

  it("marks active link based on pathname", () => {
    mockUsePathname.mockReturnValue("/w/ws-1/sources");
    render(<WorkspaceSidebar {...defaultProps} />);

    const sourcesLink = screen.getByRole("link", { name: /원문 소스/ });
    expect(sourcesLink).toHaveAttribute("aria-current", "page");
    expect(sourcesLink.className).toContain("active");
  });

  it("calls onCloseMobile when navigation item is clicked", () => {
    const onCloseMobile = vi.fn();
    render(
      <WorkspaceSidebar
        {...defaultProps}
        onCloseMobile={onCloseMobile}
        isOpenMobile={true}
      />,
    );

    const homeLink = screen.getByRole("link", { name: /홈 대시보드/ });
    fireEvent.click(homeLink);

    expect(onCloseMobile).toHaveBeenCalledTimes(1);
  });
});

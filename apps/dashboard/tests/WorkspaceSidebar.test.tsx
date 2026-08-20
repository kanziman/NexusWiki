import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

const mockUsePathname = vi.hoisted(() => vi.fn(() => "/w/ws-1"));
const mockSearchParamsGet = vi.hoisted(() =>
  vi.fn<(key: string) => string | null>(() => null),
);

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
    workspaces: [
      { id: "ws-1", name: "테스트 워크스페이스", kind: "personal" as const },
    ],
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
    expect(screen.getByRole("link", { name: /즐겨찾기/ })).toHaveAttribute(
      "href",
      "/w/ws-1/wiki?bookmarked=true",
    );

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

  it("위키 문서 경로에서 bookmarked=true면 즐겨찾기 링크만 active로 표시한다", () => {
    mockUsePathname.mockReturnValue("/w/ws-1/wiki");
    mockSearchParamsGet.mockImplementation((key: string) =>
      key === "bookmarked" ? "true" : null,
    );
    render(<WorkspaceSidebar {...defaultProps} />);

    const bookmarkedLink = screen.getByRole("link", { name: /즐겨찾기/ });
    const wikiLink = screen.getByRole("link", { name: /위키 문서/ });
    expect(bookmarkedLink).toHaveAttribute("aria-current", "page");
    expect(bookmarkedLink.className).toContain("active");
    expect(wikiLink).not.toHaveAttribute("aria-current");
    expect(wikiLink.className).not.toContain("active");

    mockSearchParamsGet.mockReturnValue(null);
  });

  it("접기 토글은 onToggleCollapsed가 있을 때만 렌더링되고, collapsed 상태를 sidebar 클래스에 반영한다 (UX-03)", () => {
    const onToggleCollapsed = vi.fn();
    const { rerender } = render(<WorkspaceSidebar {...defaultProps} />);

    expect(
      screen.queryByRole("button", { name: /메뉴 접기|메뉴 펼치기/ }),
    ).not.toBeInTheDocument();

    rerender(
      <WorkspaceSidebar
        {...defaultProps}
        collapsed={false}
        onToggleCollapsed={onToggleCollapsed}
      />,
    );

    const toggle = screen.getByRole("button", { name: "메뉴 접기" });
    fireEvent.click(toggle);
    expect(onToggleCollapsed).toHaveBeenCalledTimes(1);
    expect(screen.getByRole("complementary").className).not.toContain(
      "collapsed",
    );

    rerender(
      <WorkspaceSidebar
        {...defaultProps}
        collapsed={true}
        onToggleCollapsed={onToggleCollapsed}
      />,
    );

    expect(
      screen.getByRole("button", { name: "메뉴 펼치기" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("complementary").className).toContain("collapsed");
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

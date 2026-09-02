import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mockUsePathname = vi.hoisted(() => vi.fn(() => "/w/ws-1"));
const mockSearchParamsGet = vi.hoisted(() =>
  vi.fn<(key: string) => string | null>(() => null),
);
const push = vi.hoisted(() => vi.fn());

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
  usePathname: mockUsePathname,
  useSearchParams: () => ({
    get: mockSearchParamsGet,
  }),
}));

vi.mock("@/components/WorkspaceSwitcher", () => ({
  WorkspaceSwitcher: ({ workspaces }: { workspaces: { name: string }[] }) => (
    <button
      type="button"
      data-testid="workspace-switcher"
      aria-label={workspaces[0]?.name}
    >
      {workspaces[0]?.name}
    </button>
  ),
}));

vi.mock("@/lib/api-client", () => ({
  apiFetch: vi.fn(async (path: string) => {
    if (path.includes("/budget")) {
      return {
        cap_micros: 5000000,
        spent_micros: 1500000,
        remaining_micros: 3500000,
        month_start: "2026-08-01T00:00:00Z",
        truncated: false,
        authoritative: false,
      };
    }
    return [];
  }),
}));

vi.mock("@/lib/ask-threads", () => ({
  listAskThreads: vi.fn(async () => [
    {
      id: "thread-101",
      title: "최근 질문 1",
      created_at: "2026-08-23T00:00:00Z",
      updated_at: "2026-08-23T00:00:00Z",
    },
    {
      id: "thread-102",
      title: "최근 질문 2",
      created_at: "2026-08-23T00:00:00Z",
      updated_at: "2026-08-23T00:00:00Z",
    },
  ]),
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

  beforeEach(() => {
    push.mockReset();
    sessionStorage.clear();
    mockUsePathname.mockReturnValue("/w/ws-1");
    mockSearchParamsGet.mockReturnValue(null);
  });

  it("질문하기를 다시 누르면 세션의 활성 스레드로 이동한다", () => {
    sessionStorage.setItem(
      "nexuswiki:active-ask-thread:ws-1",
      "thread-streaming-1",
    );
    render(<WorkspaceSidebar {...defaultProps} />);

    fireEvent.click(screen.getByRole("link", { name: "질문하기" }));

    expect(push).toHaveBeenCalledWith("/w/ws-1/ask?thread=thread-streaming-1");
  });

  it("renders main navigation items, categories, and user profile", () => {
    render(<WorkspaceSidebar {...defaultProps} />);

    expect(screen.getByText("테스트 워크스페이스")).toBeInTheDocument();

    expect(
      screen.getByRole("link", { name: /홈 대시보드/ }),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /원문 소스/ })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /질문하기/ })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /위키 문서/ })).toBeInTheDocument();
    // aria-label 이 접근성 이름을 덮으므로 getByRole 은 그쪽만 본다. 보이는
    // 라벨을 따로 단언해, 둘이 갈라지면(예: 눈에 보이는 문구만 바꾸는 경우)
    // 스크린리더 사용자에게 옛 명칭이 남는 상황을 잡는다.
    const backlogLink = screen.getByRole("link", { name: "지식 공백" });
    expect(backlogLink).toBeInTheDocument();
    expect(backlogLink).toHaveTextContent("지식 공백");
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

  it("LNB에서 최근 대화 목록을 렌더링하고 클릭 시 해당 스레드로 이동 링크를 제공한다", async () => {
    render(<WorkspaceSidebar {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText("최근 질문 1")).toBeInTheDocument();
      expect(screen.getByText("최근 질문 2")).toBeInTheDocument();
    });

    const threadLink = screen.getByRole("link", { name: /최근 질문 1/ });
    expect(threadLink).toHaveAttribute("href", "/w/ws-1/ask?thread=thread-101");
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

  it("접힌 상태에서도 내비게이션과 계정 설정을 키보드로 식별하고 조작할 수 있다", () => {
    render(
      <WorkspaceSidebar
        {...defaultProps}
        collapsed
        onToggleCollapsed={vi.fn()}
      />,
    );

    const home = screen.getByRole("link", { name: "홈 대시보드" });
    const settings = screen.getByRole("link", { name: "팀원 & 역할 관리" });
    const switcher = screen.getByRole("button", {
      name: "테스트 워크스페이스",
    });

    home.focus();
    expect(home).toHaveFocus();
    expect(home).toHaveAttribute("aria-label", "홈 대시보드");

    settings.focus();
    expect(settings).toHaveFocus();
    expect(settings).toHaveAttribute("href", "/w/ws-1/settings");

    switcher.focus();
    expect(switcher).toHaveFocus();
  });

  it("모바일 서랍이 열려 있으면 collapsed=true여도 collapsed 클래스나 접기 토글을 그리지 않는다 (/code-review 지적)", () => {
    render(
      <WorkspaceSidebar
        {...defaultProps}
        collapsed={true}
        onToggleCollapsed={vi.fn()}
        isOpenMobile={true}
      />,
    );

    const aside = screen.getByRole("complementary");
    expect(aside.className).toContain("mobile-open");
    expect(aside.className).not.toContain("collapsed");
    expect(
      screen.queryByRole("button", { name: /메뉴 접기|메뉴 펼치기/ }),
    ).not.toBeInTheDocument();
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

  it("사이드바 하단에 잔여 무료 크레딧 위젯을 렌더링한다", async () => {
    render(<WorkspaceSidebar {...defaultProps} />);

    expect(await screen.findByText("무료 크레딧")).toBeInTheDocument();
    expect(screen.getByText("350 크레딧 남음")).toBeInTheDocument();
    expect(screen.getByText("30%")).toBeInTheDocument();
  });

  it("커스텀 API 키가 등록된 워크스페이스는 '내 API 키 연결됨 (무제한)' 위젯을 렌더링한다", async () => {
    const { apiFetch } = await import("@/lib/api-client");
    vi.mocked(apiFetch).mockResolvedValueOnce({
      cap_micros: -1,
      spent_micros: 0,
      remaining_micros: -1,
      month_start: "2026-08-01T00:00:00Z",
      truncated: false,
      authoritative: false,
    });

    render(<WorkspaceSidebar {...defaultProps} />);

    expect(await screen.findByText("내 API 키 연결됨")).toBeInTheDocument();
    expect(screen.getByText("무제한 이용 중")).toBeInTheDocument();
  });
});

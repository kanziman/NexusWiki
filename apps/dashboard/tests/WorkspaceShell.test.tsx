import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => "/w/ws-1",
  useSearchParams: () => ({
    get: () => null,
  }),
}));

vi.mock("@/components/WorkspaceSwitcher", () => ({
  WorkspaceSwitcher: ({ workspaces }: { workspaces: { name: string }[] }) => (
    <div>{workspaces[0]?.name}</div>
  ),
}));

vi.mock("@/lib/supabase/client", () => ({
  createClient: () => ({ auth: { signOut: vi.fn() } }),
}));

import { WorkspaceShell } from "@/components/WorkspaceShell";

describe("WorkspaceShell", () => {
  const defaultProps = {
    workspace: { id: "ws-1", name: "우리 팀 워크스페이스" },
    workspaces: [
      { id: "ws-1", name: "우리 팀 워크스페이스", kind: "team" as const },
    ],
    currentWorkspaceId: "ws-1",
    accountEmail: "tester@example.com",
  };

  beforeEach(() => {
    sessionStorage.clear();
  });

  it("renders topbar actions, breadcrumb, and children content", () => {
    render(
      <WorkspaceShell {...defaultProps}>
        <div data-testid="test-content">메인 콘텐츠</div>
      </WorkspaceShell>,
    );

    const topbar = document.querySelector('[data-od-id="workspace-topbar"]');
    expect(topbar).toHaveTextContent("우리 팀 워크스페이스");
    expect(topbar).toHaveTextContent("홈 대시보드");
    expect(screen.getByRole("link", { name: /소스 추가/ })).toHaveAttribute(
      "href",
      "/w/ws-1/sources",
    );
    expect(screen.getByRole("link", { name: /질문 시작/ })).toHaveAttribute(
      "href",
      "/w/ws-1/ask",
    );
    expect(screen.getByTestId("test-content")).toBeInTheDocument();
  });

  it("exposes the account affordance in the header (account-session-control)", () => {
    render(
      <WorkspaceShell {...defaultProps}>
        <div>콘텐츠</div>
      </WorkspaceShell>,
    );

    expect(
      screen.getByRole("button", { name: "계정 메뉴" }),
    ).toBeInTheDocument();
  });

  it("toggles mobile menu and closes on scrim click", () => {
    render(
      <WorkspaceShell {...defaultProps}>
        <div>콘텐츠</div>
      </WorkspaceShell>,
    );

    const mobileMenuBtn = screen.getByRole("button", { name: "메뉴 열기" });
    fireEvent.click(mobileMenuBtn);

    expect(
      screen.getByRole("button", { name: "메뉴 닫기" }),
    ).toBeInTheDocument();

    const aside = screen.getByRole("complementary");
    expect(aside.className).toContain("mobile-open");

    // Click scrim to close
    const scrim = document.querySelector(".mobile-scrim");
    expect(scrim).not.toBeNull();
    if (scrim) {
      fireEvent.click(scrim);
    }

    expect(
      screen.getByRole("button", { name: "메뉴 열기" }),
    ).toBeInTheDocument();
    expect(aside.className).not.toContain("mobile-open");
  });

  it("toggles LNB collapse and persists the choice to sessionStorage (UX-03)", () => {
    render(
      <WorkspaceShell {...defaultProps}>
        <div>콘텐츠</div>
      </WorkspaceShell>,
    );

    function getApp() {
      const el = document.querySelector('[data-od-id="nexuswiki-workspace"]');
      if (!el) throw new Error("app root not found");
      return el;
    }

    expect(getApp().className).not.toContain("sidebar-collapsed");

    fireEvent.click(screen.getByRole("button", { name: "메뉴 접기" }));

    expect(getApp().className).toContain("sidebar-collapsed");
    expect(screen.getByRole("complementary").className).toContain("collapsed");
    expect(
      screen.getByRole("button", { name: "메뉴 펼치기" }),
    ).toBeInTheDocument();
    expect(sessionStorage.getItem("nexuswiki-lnb-collapsed")).toBe("true");

    fireEvent.click(screen.getByRole("button", { name: "메뉴 펼치기" }));

    expect(getApp().className).not.toContain("sidebar-collapsed");
    expect(sessionStorage.getItem("nexuswiki-lnb-collapsed")).toBe("false");
  });

  it("restores a collapsed LNB from sessionStorage on mount", () => {
    sessionStorage.setItem("nexuswiki-lnb-collapsed", "true");

    render(
      <WorkspaceShell {...defaultProps}>
        <div>콘텐츠</div>
      </WorkspaceShell>,
    );

    expect(
      screen.getByRole("button", { name: "메뉴 펼치기" }),
    ).toBeInTheDocument();
  });

  // dashboard-design-consistency 「Constrained global knowledge actions」의
  // 회귀 방지. 이 요구사항은 현재 동작을 명문화한 것이라 구현 변경이 없었고,
  // 그래서 테스트가 없으면 다음 사람이 전역 바에 액션을 하나 더 얹어도
  // 아무것도 막지 않는다. 계정·모바일 내비는 요구사항이 제외한 항목이다.
  it("전역 행동 바에 지식 액션은 소스 추가·질문 시작 둘뿐이다", () => {
    render(
      <WorkspaceShell {...defaultProps}>
        <div>콘텐츠</div>
      </WorkspaceShell>,
    );

    const topbar = document.querySelector(
      '[data-od-id="workspace-topbar"]',
    ) as HTMLElement;
    // ⚠️ <a> 만 세지 않는다 — 지식 액션이 <button> 으로 추가되면 그것도
    // 전역 바에 쌓인 것이다. 계정 메뉴·모바일 내비는 요구사항이 제외한
    // 항목이라 aria-label 로 걸러낸다.
    const actionLabels = Array.from(
      topbar.querySelectorAll<HTMLElement>(
        ".top-actions a, .top-actions > button",
      ),
    )
      .filter((el) => !el.closest("[data-od-id='account-menu']"))
      .filter((el) => el.getAttribute("aria-label") === null)
      .map((el) => el.textContent?.trim());

    expect(actionLabels).toEqual(["소스 추가", "질문 시작"]);
  });
});

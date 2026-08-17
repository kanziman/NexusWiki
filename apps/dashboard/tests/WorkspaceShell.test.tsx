import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({
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

import { WorkspaceShell } from "@/components/WorkspaceShell";

describe("WorkspaceShell", () => {
  const defaultProps = {
    workspace: { id: "ws-1", name: "우리 팀 워크스페이스" },
    workspaces: [{ id: "ws-1", name: "우리 팀 워크스페이스" }],
    currentWorkspaceId: "ws-1",
    accountEmail: "tester@example.com",
  };

  it("renders topbar actions, breadcrumb, and children content", () => {
    render(
      <WorkspaceShell {...defaultProps}>
        <div data-testid="test-content">메인 콘텐츠</div>
      </WorkspaceShell>,
    );

    expect(
      screen.getAllByText("우리 팀 워크스페이스").length,
    ).toBeGreaterThanOrEqual(1);
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
});

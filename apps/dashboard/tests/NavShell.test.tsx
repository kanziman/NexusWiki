import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({
  usePathname: () => "/w/ws-1/sources",
}));

vi.mock("@/components/WorkspaceSwitcher", () => ({
  WorkspaceSwitcher: ({ workspaces }: { workspaces: { name: string }[] }) => (
    <button type="button">{workspaces[0]?.name}</button>
  ),
}));

import { NavShell } from "@/components/NavShell";

describe("NavShell", () => {
  it("marks the current route with semantic and visual active state", () => {
    render(
      <NavShell
        currentWorkspaceId="ws-1"
        workspaces={[{ id: "ws-1", name: "내 워크스페이스" }]}
      />,
    );

    for (const label of ["소스", "질문하기", "위키", "그래프", "설정"]) {
      expect(screen.getByRole("link", { name: label })).toBeInTheDocument();
    }

    expect(screen.getByRole("link", { name: "소스" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(screen.getByRole("link", { name: "소스" })).toHaveAttribute(
      "data-active",
      "true",
    );
    expect(screen.getByRole("link", { name: "설정" })).not.toHaveAttribute(
      "aria-current",
    );
  });
});

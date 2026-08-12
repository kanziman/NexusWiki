import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

// D-03과 같은 패턴으로 next/navigation을 모킹해 push 호출 인자(즉 URL의
// ?category= 파라미터)를 직접 관찰한다 — WorkspaceSwitcher.test.tsx와 동일한
// 모킹 전략.
const push = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
  usePathname: () => "/w/ws-1/graph",
  useSearchParams: () => new URLSearchParams(),
}));

import { GraphLensFilter } from "@/components/GraphLensFilter";

describe("GraphLensFilter", () => {
  beforeEach(() => {
    push.mockReset();
  });

  it("activeCategory가 null일 때 '개념' 칩을 클릭하면 category=concepts로 이동한다", async () => {
    const user = userEvent.setup();
    render(<GraphLensFilter workspaceId="ws-1" activeCategory={null} />);

    await user.click(screen.getByRole("button", { name: "개념" }));

    expect(push).toHaveBeenCalledWith("/w/ws-1/graph?category=concepts");
  });

  it("이미 활성인 칩을 다시 클릭하면 category 파라미터가 제거된 URL로 이동한다", async () => {
    const user = userEvent.setup();
    render(<GraphLensFilter workspaceId="ws-1" activeCategory="concepts" />);

    await user.click(screen.getByRole("button", { name: "개념" }));

    expect(push).toHaveBeenCalledWith("/w/ws-1/graph");
  });

  it("활성 칩만 data-active와 aria-pressed=true를 갖는다", () => {
    render(<GraphLensFilter workspaceId="ws-1" activeCategory="guides" />);

    const activeChip = screen.getByRole("button", { name: "가이드" });
    expect(activeChip).toHaveAttribute("data-active", "true");
    expect(activeChip).toHaveAttribute("aria-pressed", "true");

    const inactiveChip = screen.getByRole("button", { name: "개념" });
    expect(inactiveChip).not.toHaveAttribute("data-active");
    expect(inactiveChip).toHaveAttribute("aria-pressed", "false");
  });

  it("다른 카테고리 칩을 클릭하면 이전 활성 칩 대신 새 카테고리로 교체된다", async () => {
    const user = userEvent.setup();
    render(<GraphLensFilter workspaceId="ws-1" activeCategory="concepts" />);

    await user.click(screen.getByRole("button", { name: "엔티티" }));

    expect(push).toHaveBeenCalledWith("/w/ws-1/graph?category=entities");
  });
});

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const push = vi.fn();
let currentParams = new URLSearchParams();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
  usePathname: () => "/w/ws-1/ask",
  useSearchParams: () => currentParams,
}));

// GraphCanvas는 cytoscape로 실제 DOM 캔버스를 마운트한다 — 이 테스트는
// ContentViewer가 올바른 props로 위임하는지만 확인하면 되므로 얇은 스텁으로
// 대체한다(GraphLensFilter.test.tsx가 GraphLensFilter 자체를 단독 테스트하는
// 것과 같은 분리 전략).
vi.mock("@/components/GraphCanvas", () => ({
  GraphCanvas: (props: {
    layoutName?: string;
    rootSlug?: string;
    category: string | null;
  }) => (
    <div
      data-testid="graph-canvas-stub"
      data-layout={props.layoutName}
      data-root={props.rootSlug}
    />
  ),
}));

vi.mock("@/components/GraphLensFilter", () => ({
  GraphLensFilter: () => <div data-testid="graph-lens-filter-stub" />,
}));

vi.mock("@/components/WikiPageContent", () => ({
  WikiPageContent: ({ page }: { page: { title: string } }) => (
    <div data-testid="wiki-page-content-stub">{page.title}</div>
  ),
}));

vi.mock("@/lib/supabase/client", () => ({
  createClient: () => ({
    from: () => ({
      select: () => ({
        eq: () => ({
          eq: () => ({ single: async () => ({ data: null, error: null }) }),
        }),
      }),
    }),
  }),
}));

import { ContentViewer } from "@/components/ContentViewer";

describe("ContentViewer", () => {
  beforeEach(() => {
    push.mockReset();
  });

  it("shows an empty state on the wiki tab when no slug is selected", () => {
    currentParams = new URLSearchParams();
    render(<ContentViewer workspaceId="ws-1" />);

    expect(screen.getByText("위키 문서를 선택하세요")).toBeInTheDocument();
  });

  it("switching tabs pushes the updated tab query param, preserving the pane", async () => {
    currentParams = new URLSearchParams("tab=wiki");
    const user = userEvent.setup();
    render(<ContentViewer workspaceId="ws-1" />);

    await user.click(screen.getByRole("tab", { name: "2D 지식 그래프" }));

    expect(push).toHaveBeenCalledWith("/w/ws-1/ask?tab=graph");
  });

  it("renders the graph tab's filter and canvas regions", () => {
    currentParams = new URLSearchParams("tab=graph");
    render(<ContentViewer workspaceId="ws-1" />);

    expect(screen.getByTestId("graph-lens-filter-stub")).toBeInTheDocument();
    expect(screen.getByTestId("graph-canvas-stub")).toBeInTheDocument();
  });

  it("the mindmap tab renders GraphCanvas with a breadthfirst layout rooted at the active slug", () => {
    currentParams = new URLSearchParams("tab=mindmap&slug=meeting-notes");
    render(<ContentViewer workspaceId="ws-1" />);

    const canvas = screen.getByTestId("graph-canvas-stub");
    expect(canvas).toHaveAttribute("data-layout", "breadthfirst");
    expect(canvas).toHaveAttribute("data-root", "meeting-notes");
  });

  it("the mindmap tab shows an empty state when no wiki page is selected", () => {
    currentParams = new URLSearchParams("tab=mindmap");
    render(<ContentViewer workspaceId="ws-1" />);

    expect(
      screen.getByText("마인드맵은 특정 위키 문서를 중심으로 그려집니다."),
    ).toBeInTheDocument();
  });

  it("wires each tab to its panel via aria-controls/aria-labelledby and applies roving tabIndex", () => {
    currentParams = new URLSearchParams("tab=graph");
    render(<ContentViewer workspaceId="ws-1" />);

    const activeTab = screen.getByRole("tab", { name: "2D 지식 그래프" });
    const inactiveTab = screen.getByRole("tab", { name: "위키 문서" });
    const panel = screen.getByRole("tabpanel");

    expect(activeTab).toHaveAttribute("tabIndex", "0");
    expect(inactiveTab).toHaveAttribute("tabIndex", "-1");
    expect(activeTab.getAttribute("aria-controls")).toBe(panel.id);
    expect(panel.getAttribute("aria-labelledby")).toBe(activeTab.id);
  });

  it("ArrowRight on the active tab pushes the next tab and moves focus to it", async () => {
    currentParams = new URLSearchParams("tab=wiki");
    const user = userEvent.setup();
    render(<ContentViewer workspaceId="ws-1" />);

    screen.getByRole("tab", { name: "위키 문서" }).focus();
    await user.keyboard("{ArrowRight}");

    expect(push).toHaveBeenCalledWith("/w/ws-1/ask?tab=source");
    expect(screen.getByRole("tab", { name: "원시 소스" })).toHaveFocus();
  });

  it("ArrowLeft wraps from the first tab to the last tab", async () => {
    currentParams = new URLSearchParams("tab=wiki");
    const user = userEvent.setup();
    render(<ContentViewer workspaceId="ws-1" />);

    screen.getByRole("tab", { name: "위키 문서" }).focus();
    await user.keyboard("{ArrowLeft}");

    expect(push).toHaveBeenCalledWith("/w/ws-1/ask?tab=mindmap");
    expect(screen.getByRole("tab", { name: "마인드맵" })).toHaveFocus();
  });
});

import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { PreviewWorkspace } from "@/components/PreviewWorkspace";

describe("PreviewWorkspace", () => {
  it("renders a mock workspace whose navigation stays under /preview", () => {
    render(<PreviewWorkspace path={[]} />);

    expect(
      screen.getByText("NexusWiki 제품 탐색", { selector: "strong" }),
    ).toBeInTheDocument();
    expect(
      within(
        screen.getByRole("navigation", { name: "미리보기 탐색" }),
      ).getByRole("link", { name: "질문하기" }),
    ).toHaveAttribute("href", "/preview/ask");
    expect(screen.getByRole("link", { name: /이중 인용/ })).toHaveAttribute(
      "href",
      "/preview/wiki/double-citation",
    );
    expect(screen.getByText("지식 그래프")).toBeInTheDocument();
    expect(screen.getByText("4개 노드 · 4개 연결")).toBeInTheDocument();
  });

  it("미리보기 홈은 실제 홈과 같은 .sections 그리드를 공유한다", () => {
    const { container } = render(<PreviewWorkspace path={[]} />);
    const sections = container.querySelector(".sections");

    expect(sections).not.toBeNull();
    expect(sections?.children).toHaveLength(2);
    expect(screen.getByText(/컴파일된 위키 문서/)).toBeInTheDocument();
    expect(screen.getByText(/작성 대기 백로그/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /이중 인용/ })).toBeInTheDocument();
    expect(screen.getByText("평가 루프")).toBeInTheDocument();
  });

  it("shows deterministic Ask evidence without a network request", () => {
    const fetchSpy = vi.fn();
    vi.stubGlobal("fetch", fetchSpy);
    render(<PreviewWorkspace path={["ask"]} />);

    fireEvent.click(
      screen.getByRole("button", { name: "원문 · 2026 Q3 제품 리서치.pdf" }),
    );

    expect(
      screen.getByText("원문 청크 03 · 1,240–1,834자"),
    ).toBeInTheDocument();
    expect(fetchSpy).not.toHaveBeenCalled();
    vi.unstubAllGlobals();
  });

  it("blocks mock upload from making an external request", () => {
    const fetchSpy = vi.fn();
    vi.stubGlobal("fetch", fetchSpy);
    render(<PreviewWorkspace path={["sources"]} />);

    fireEvent.click(screen.getByRole("button", { name: "소스 업로드" }));

    expect(screen.getByRole("status")).toHaveTextContent(
      "미리보기에서는 업로드되지 않습니다.",
    );
    expect(fetchSpy).not.toHaveBeenCalled();
    vi.unstubAllGlobals();
  });

  it("replaces every preview mutation affordance with a local notice", () => {
    render(<PreviewWorkspace path={["settings"]} />);

    fireEvent.click(screen.getByRole("button", { name: "멤버 초대" }));
    expect(screen.getByRole("status")).toHaveTextContent(
      "미리보기에서는 초대되지 않습니다.",
    );

    fireEvent.click(screen.getByRole("button", { name: "설정 저장" }));
    expect(screen.getByRole("status")).toHaveTextContent(
      "미리보기에서는 저장되지 않습니다.",
    );
  });
});

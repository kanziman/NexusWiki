import { fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("@/app/bookmark-actions", () => ({
  setWikiBookmark: vi.fn(),
}));

import { WikiPageContent } from "@/components/WikiPageContent";

describe("WikiPageContent", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders document context, heading navigation, and resolved related pages", () => {
    render(
      <WikiPageContent
        workspaceId="ws-1"
        canVerify={false}
        initialBookmarked={false}
        page={{
          id: "one",
          title: "문서",
          category: "guides",
          content: "# 개요\n본문 [[관련 문서]]",
          verification_status: "unverified",
          verified_by: null,
          verified_at: null,
          expires_at: null,
          disputed: false,
        }}
        links={[{ target_slug: "관련-문서", resolved: true }]}
      />,
    );
    expect(
      screen.getByRole("link", { name: "위키 목록으로 돌아가기" }),
    ).toHaveAttribute("href", "/w/ws-1/wiki");
    expect(
      screen.getByRole("navigation", { name: "위키 탐색 경로" }),
    ).toHaveTextContent("가이드");
    expect(
      screen.getByRole("navigation", { name: "이 문서에서" }),
    ).toHaveTextContent("개요");
    expect(screen.getByRole("region", { name: "관련 문서" })).toHaveTextContent(
      "관련 문서",
    );
  });

  it("마크다운 본문 끝의 '## 관련 문서' 섹션을 제거하여 하단 카드 칩과 중복되지 않게 한다", () => {
    const rawMarkdown = `## 핵심 개념
개념 설명입니다.

## 관련 문서
- [[데이터-계층]]
- [[시스템-아키텍처]]
`;

    render(
      <WikiPageContent
        workspaceId="ws-1"
        canVerify={false}
        initialBookmarked={false}
        page={{
          id: "one",
          title: "문서",
          category: "concepts",
          content: rawMarkdown,
          verification_status: "verified",
          verified_by: null,
          verified_at: null,
          expires_at: null,
          disputed: false,
        }}
        links={[
          { target_slug: "데이터-계층", resolved: true },
          { target_slug: "시스템-아키텍처", resolved: true },
        ]}
      />,
    );

    // 본문 TOC 목차에는 "핵심 개념"만 있고 "관련 문서"는 목차에서 제외됨
    const toc = screen.getByRole("navigation", { name: "이 문서에서" });
    expect(within(toc).getByText("핵심 개념")).toBeInTheDocument();
    expect(within(toc).queryByText("관련 문서")).toBeNull();

    // 하단 전용 영역에만 "관련 문서" 칩이 렌더링됨
    const relatedSection = screen.getByRole("region", { name: "관련 문서" });
    expect(relatedSection).toBeInTheDocument();
    expect(within(relatedSection).getByText("데이터 계층")).toBeInTheDocument();
    expect(
      within(relatedSection).getByText("시스템 아키텍처"),
    ).toBeInTheDocument();
  });

  it("exposes a favorite toggle in the title row (UX-02)", () => {
    render(
      <WikiPageContent
        workspaceId="ws-1"
        canVerify={false}
        initialBookmarked={true}
        page={{
          id: "one",
          title: "문서",
          category: "guides",
          content: "본문",
          verification_status: "unverified",
          verified_by: null,
          verified_at: null,
          expires_at: null,
          disputed: false,
        }}
        links={[]}
      />,
    );

    expect(
      screen.getByRole("button", { name: "즐겨찾기 해제" }),
    ).toBeInTheDocument();
  });

  it("renders markdown elements including tables, lists, quotes, and code blocks with rich links", () => {
    const markdownContent = `
## 사업 개요
- **발주사**: 현대자동차
- **사업 기간**: 2026 ~ 2027

> 중요 프로젝트 개요입니다.

| 구분 | 내용 |
|---|---|
| OS | Rocky Linux |
| DBMS | PostgreSQL |

\`\`\`bash
npm run build
\`\`\`
`;

    render(
      <WikiPageContent
        workspaceId="ws-1"
        canVerify={false}
        initialBookmarked={false}
        page={{
          id: "two",
          title: "Connect 수집 IBD 사양",
          category: "entities",
          content: markdownContent,
          verification_status: "verified",
          verified_by: null,
          verified_at: "2026-08-20T00:00:00Z",
          expires_at: null,
          disputed: false,
        }}
        links={[]}
      />,
    );

    expect(screen.getByRole("table")).toBeInTheDocument();
    expect(screen.getByText("Rocky Linux")).toBeInTheDocument();
    expect(screen.getByText("PostgreSQL")).toBeInTheDocument();
    expect(screen.getByText("발주사")).toBeInTheDocument();
    expect(screen.getByText(/: 현대자동차/)).toBeInTheDocument();
    expect(screen.getByText("중요 프로젝트 개요입니다.")).toBeInTheDocument();
    expect(screen.getByText("npm run build")).toBeInTheDocument();
  });

  it("does not make executable markdown URLs navigable", () => {
    render(
      <WikiPageContent
        workspaceId="ws-1"
        canVerify={false}
        initialBookmarked={false}
        page={{
          id: "unsafe-link",
          title: "안전 링크",
          category: "guides",
          content:
            "[안전한 문서](https://example.com/docs)와 [위험한 링크](javascript:alert(1))",
          verification_status: "unverified",
          verified_by: null,
          verified_at: null,
          expires_at: null,
          disputed: false,
        }}
        links={[]}
      />,
    );

    expect(screen.getByRole("link", { name: "안전한 문서" })).toHaveAttribute(
      "href",
      "https://example.com/docs",
    );
    expect(screen.getByText("위험한 링크").closest("a")).toBeNull();
  });

  it("tracks nested headings and updates smooth-scroll fragment navigation", () => {
    let nestedHeadingTop = 1_000;
    vi.spyOn(HTMLElement.prototype, "getBoundingClientRect").mockImplementation(
      function (this: HTMLElement) {
        const top = this.id === "section-2" ? nestedHeadingTop : 0;
        return {
          x: 0,
          y: top,
          top,
          right: 0,
          bottom: top,
          left: 0,
          width: 0,
          height: 0,
          toJSON: () => ({}),
        };
      },
    );
    const pushState = vi.spyOn(window.history, "pushState");

    render(
      <WikiPageContent
        workspaceId="ws-1"
        canVerify={false}
        initialBookmarked={false}
        page={{
          id: "toc",
          title: "목차 문서",
          category: "guides",
          content: "## 개요\n본문\n### 세부 항목",
          verification_status: "unverified",
          verified_by: null,
          verified_at: null,
          expires_at: null,
          disputed: false,
        }}
        links={[]}
      />,
    );

    const toc = screen.getByRole("navigation", { name: "이 문서에서" });
    const overview = within(toc).getByRole("link", { name: "개요" });
    const detail = within(toc).getByRole("link", { name: "세부 항목" });
    expect(overview.className).toContain("active");
    expect(overview.className).toContain("pl-2");
    expect(detail.className).toContain("pl-4");

    nestedHeadingTop = 0;
    fireEvent.scroll(window);
    expect(detail.className).toContain("active");

    const target = document.getElementById("section-2");
    expect(target).not.toBeNull();
    const scrollIntoView = vi.fn();
    if (target) target.scrollIntoView = scrollIntoView;
    fireEvent.click(detail);

    expect(scrollIntoView).toHaveBeenCalledWith({ behavior: "smooth" });
    expect(pushState).toHaveBeenCalledWith(null, "", "#section-2");
  });

  it("renders no empty section links when the document has no headings", () => {
    render(
      <WikiPageContent
        workspaceId="ws-1"
        canVerify={false}
        initialBookmarked={false}
        page={{
          id: "no-toc",
          title: "제목 없는 본문",
          category: "guides",
          content: "일반 문단만 있습니다.",
          verification_status: "unverified",
          verified_by: null,
          verified_at: null,
          expires_at: null,
          disputed: false,
        }}
        links={[]}
      />,
    );

    const toc = screen.getByRole("complementary");
    expect(within(toc).queryAllByRole("link")).toHaveLength(0);
    expect(
      within(toc).getByText("제목이 없는 문서입니다."),
    ).toBeInTheDocument();
  });
});

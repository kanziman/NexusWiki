import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("@/app/bookmark-actions", () => ({
  setWikiBookmark: vi.fn(),
}));

import { WikiPageContent } from "@/components/WikiPageContent";

describe("WikiPageContent", () => {
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
      screen.getByRole("navigation", { name: "위키 탐색 경로" }),
    ).toHaveTextContent("위키 / guides");
    expect(
      screen.getByRole("navigation", { name: "이 문서에서" }),
    ).toHaveTextContent("개요");
    expect(screen.getByRole("region", { name: "관련 문서" })).toHaveTextContent(
      "관련 문서",
    );
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
});

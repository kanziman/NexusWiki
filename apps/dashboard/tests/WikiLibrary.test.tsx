import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { WikiLibrary } from "@/components/WikiLibrary";

const pages = [
  {
    id: "one",
    slug: "sso",
    title: "SSO 가이드",
    category: "guides",
    content: "인증 연결 방법",
    verification_status: "verified",
    disputed: false,
  },
  {
    id: "two",
    slug: "data",
    title: "데이터 모델",
    category: "concepts",
    content: "엔터티 관계",
    verification_status: "unverified",
    disputed: false,
  },
];

describe("WikiLibrary", () => {
  it("filters loaded workspace pages by text and category", () => {
    render(<WikiLibrary pages={pages} workspaceId="ws-1" />);
    fireEvent.change(screen.getByRole("textbox", { name: "위키 문서 검색" }), {
      target: { value: "인증" },
    });
    expect(screen.getByRole("link", { name: /SSO 가이드/ })).toHaveAttribute(
      "href",
      "/w/ws-1/wiki/sso",
    );
    expect(screen.queryByText("데이터 모델")).not.toBeInTheDocument();
    fireEvent.change(screen.getByRole("textbox", { name: "위키 문서 검색" }), {
      target: { value: "" },
    });
    fireEvent.click(screen.getByRole("button", { name: "개념" }));
    expect(screen.getByText("데이터 모델")).toBeInTheDocument();
    expect(screen.queryByText("SSO 가이드")).not.toBeInTheDocument();
  });

  it("shows a distinct no-results state", () => {
    render(<WikiLibrary pages={pages} workspaceId="ws-1" />);
    fireEvent.change(screen.getByRole("textbox", { name: "위키 문서 검색" }), {
      target: { value: "없는 문서" },
    });
    expect(screen.getByRole("status")).toHaveTextContent(
      "조건에 맞는 위키 문서가 없습니다.",
    );
  });
});

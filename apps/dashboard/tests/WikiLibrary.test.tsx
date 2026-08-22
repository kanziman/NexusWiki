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

  it("문서가 하나도 없을 때 UI-SPEC 빈 상태 문구를 페이지 프레임 안에서 렌더링한다", () => {
    // ⚠️ 예전에는 라우트가 pages.length === 0 을 가로채 자체 마크업을 반환했고,
    // 그래서 이 문구가 페이지 프레임 없이 v1 조판으로만 떴다.
    render(<WikiLibrary pages={[]} workspaceId="ws-1" />);

    expect(
      screen.getByText("아직 컴파일된 위키 페이지가 없습니다"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("소스를 추가하면 자동으로 위키 페이지가 생성됩니다."),
    ).toBeInTheDocument();

    // 화면 프레임은 유지된다 — 제목이 있어야 다른 목적지와 위계가 같다.
    expect(
      screen.getByRole("heading", { level: 1, name: "위키" }),
    ).toBeInTheDocument();

    // 걸러낼 대상이 없으므로 검색·필터는 그리지 않는다.
    expect(
      screen.queryByRole("textbox", { name: "위키 문서 검색" }),
    ).not.toBeInTheDocument();
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

  it("uses the same cleaned markdown wording for previews and search", () => {
    render(
      <WikiLibrary
        workspaceId="ws-1"
        pages={[
          {
            ...pages[0],
            content:
              "## 인증 개요\n- **발급사**: [[identity-provider|회사 인증 서버]]",
          },
        ]}
      />,
    );

    expect(
      screen.getByText(/인증 개요 발급사: 회사 인증 서버/),
    ).toBeInTheDocument();
    expect(screen.queryByText(/\[\[/)).toBeNull();

    fireEvent.change(screen.getByRole("textbox", { name: "위키 문서 검색" }), {
      target: { value: "회사 인증 서버" },
    });
    expect(
      screen.getByRole("link", { name: /SSO 가이드/ }),
    ).toBeInTheDocument();
  });
});

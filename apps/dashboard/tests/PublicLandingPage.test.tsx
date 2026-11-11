import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { PublicLandingPage } from "@/components/PublicLandingPage";

describe("PublicLandingPage", () => {
  it("모바일 메뉴의 확장 상태를 알리고 링크 선택 시 닫는다", async () => {
    const user = userEvent.setup();
    render(<PublicLandingPage />);

    const menuButton = screen.getByRole("button", { name: "메뉴 열기" });
    expect(menuButton).toHaveAttribute("aria-expanded", "false");

    await user.click(menuButton);

    expect(screen.getByRole("button", { name: "메뉴 닫기" })).toHaveAttribute(
      "aria-expanded",
      "true",
    );
    const mobileNavigation = screen.getByRole("navigation", {
      name: "모바일 공개 랜딩 메뉴",
    });
    await user.click(
      within(mobileNavigation).getByRole("link", { name: "동작 원리" }),
    );

    expect(screen.getByRole("button", { name: "메뉴 열기" })).toHaveAttribute(
      "aria-expanded",
      "false",
    );
  });

  it("데스크톱·모바일 상단 메뉴의 FAQ 다음에 평가 기록 링크를 둔다", async () => {
    const user = userEvent.setup();
    render(<PublicLandingPage />);

    const desktopNavigation = screen.getByRole("navigation", {
      name: "공개 랜딩 주요 섹션",
    });
    const desktopLinks = within(desktopNavigation)
      .getAllByRole("link")
      .map((link) => link.textContent);
    expect(desktopLinks.slice(-2)).toEqual(["FAQ", "평가 기록"]);
    expect(
      within(desktopNavigation).getByRole("link", { name: "평가 기록" }),
    ).toHaveAttribute("href", "/showcase/evaluation");

    await user.click(screen.getByRole("button", { name: "메뉴 열기" }));
    const mobileNavigation = screen.getByRole("navigation", {
      name: "모바일 공개 랜딩 메뉴",
    });
    const mobileEvaluation = within(mobileNavigation).getByRole("link", {
      name: "평가 기록",
    });
    expect(mobileEvaluation).toHaveAttribute("href", "/showcase/evaluation");
    // 모바일 메뉴는 끝에 「로그인」이 붙으므로 FAQ 바로 다음 자리를 인덱스로 본다.
    const mobileLabels = within(mobileNavigation)
      .getAllByRole("link")
      .map((link) => link.textContent);
    expect(mobileLabels[mobileLabels.indexOf("FAQ") + 1]).toBe("평가 기록");

    await user.click(mobileEvaluation);

    expect(screen.getByRole("button", { name: "메뉴 열기" })).toHaveAttribute(
      "aria-expanded",
      "false",
    );
  });

  it("평가 기록 링크는 대상 페이지를 프리페치하지 않는다", () => {
    const source = readFileSync(
      resolve(
        process.cwd(),
        "components/public-landing/PublicLandingHeader.tsx",
      ),
      "utf8",
    );
    // 홈·로그인 링크는 프리페치 대상이므로 평가 기록 링크만 골라 본다.
    const evaluationLinks = (source.match(/<Link\b[^>]*>/g) ?? []).filter(
      (link) => link.includes("href={evaluationLink.href}"),
    );

    expect(evaluationLinks).toHaveLength(2);
    for (const link of evaluationLinks) {
      expect(link).toContain("prefetch={false}");
    }
  });

  it("쇼케이스에 공개된 두 위키 워크스페이스와 대표 문서 링크를 보여준다", () => {
    render(<PublicLandingPage />);

    expect(
      screen.getByRole("heading", { name: "공개된 지식 워크스페이스" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "스타트업 올스타" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "마케팅 올스타" }),
    ).toBeInTheDocument();

    expect(
      screen.getByRole("link", {
        name: /B2B SaaS 기업이 초기 100개 고객사를 확보한 6대 경로/,
      }),
    ).toHaveAttribute(
      "href",
      "/p/%EC%8A%A4%ED%83%80%ED%8A%B8%EC%97%85-%EC%98%AC%EC%8A%A4%ED%83%80/b2b-saas-%EA%B8%B0%EC%97%85%EC%9D%B4-%EC%B4%88%EA%B8%B0-100%EA%B0%9C-%EA%B3%A0%EA%B0%9D%EC%82%AC%EB%A5%BC-%ED%99%95%EB%B3%B4%ED%95%9C-6%EB%8C%80-%EA%B2%BD%EB%A1%9C",
    );
    expect(
      screen.getByRole("link", { name: /100의 법칙 \(The Rule of 100\)/ }),
    ).toHaveAttribute(
      "href",
      "/p/%EB%A7%88%EC%BC%80%ED%8C%85-%EC%98%AC%EC%8A%A4%ED%83%80/100%EC%9D%98-%EB%B2%95%EC%B9%99-the-rule-of-100",
    );
  });

  it("FAQ의 버튼과 답변 영역을 접근성 속성으로 연결한다", async () => {
    const user = userEvent.setup();
    render(<PublicLandingPage />);

    const question = screen.getByRole("button", {
      name: "내 워크스페이스가 다른 사용자에게 보이나요?",
    });
    expect(question).toHaveAttribute("aria-expanded", "false");

    await user.click(question);

    expect(question).toHaveAttribute("aria-expanded", "true");
    expect(
      screen.getByRole("region", { name: question.textContent ?? "" }),
    ).toHaveTextContent("Postgres RLS 정책");
  });

  it("검증되지 않은 절대 수치 문구를 노출하지 않는다", () => {
    const { container } = render(<PublicLandingPage />);

    expect(container).not.toHaveTextContent("1초 만에");
    expect(container).not.toHaveTextContent("30초 만에");
    expect(container).not.toHaveTextContent("100% 검증");
    expect(container).not.toHaveTextContent("RLS 37개");
    expect(container).not.toHaveTextContent("수백 개");
    expect(container).not.toHaveTextContent("24시간");
    expect(container).not.toHaveTextContent("항상 최신");
    expect(container).not.toHaveTextContent("신용카드 불필요");
  });

  it("섹션 소개 문단이 간격 토큰과 충돌하는 max-w-xl을 사용하지 않는다", () => {
    render(<PublicLandingPage />);

    const sectionCopy = screen.getByText(
      "개인의 지적 자산부터 팀의 핵심 문서까지 한곳에서 활용할 수 있습니다.",
    );

    expect(sectionCopy).toHaveClass("w-full", "max-w-prose");
    expect(sectionCopy).not.toHaveClass("max-w-xl");
  });
});

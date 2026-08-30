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

  it("워크스페이스와 추천 질문을 선택하면 연결된 근거 답변을 표시한다", async () => {
    const user = userEvent.setup();
    render(<PublicLandingPage />);

    const teamWorkspace = screen.getByRole("tab", {
      name: "사내 테크 & 정책 위키",
    });
    await user.click(teamWorkspace);

    expect(teamWorkspace).toHaveAttribute("aria-selected", "true");
    expect(
      screen.getByText("새 결제 정책에서 연간 계약 고객 환불 처리 규칙은?"),
    ).toBeInTheDocument();

    const isolationQuestion = screen.getByRole("button", {
      name: "DB 테넌트 격리 아키텍처 원칙",
    });
    await user.click(isolationQuestion);

    expect(isolationQuestion).toHaveAttribute("aria-pressed", "true");
    expect(
      screen.getByText(/PostgreSQL의 RLS.*요청자 JWT와 워크스페이스 멤버십/),
    ).toBeInTheDocument();
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

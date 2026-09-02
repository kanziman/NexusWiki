import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

const mockPush = vi.hoisted(() => vi.fn());

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: mockPush,
  }),
}));

import { AskHero } from "@/components/AskHero";

const HARDCODED_ENGINEERING_CHIPS = [
  "PostgreSQL RLS 격리 규칙 요약",
  "복합 외래키 전파 규칙",
  "캐시 계층 전략의 누락 항목",
];

describe("AskHero", () => {
  it("renders input, scope selector, and submit button without hardcoded chips", () => {
    render(<AskHero workspaceId="ws-1" />);

    expect(screen.getByLabelText("질문 입력")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "질문하기" }),
    ).toBeInTheDocument();
    expect(screen.getByText("워크스페이스 전체")).toBeInTheDocument();
    for (const chip of HARDCODED_ENGINEERING_CHIPS) {
      expect(
        screen.queryByRole("button", { name: chip }),
      ).not.toBeInTheDocument();
    }
  });

  it("populates textarea and focuses it when a starter chip is clicked", () => {
    const chipText = "워크스페이스 고유 질문";
    render(<AskHero workspaceId="ws-1" defaultChips={[chipText]} />);

    const chip = screen.getByRole("button", { name: chipText });
    fireEvent.click(chip);

    const textarea = screen.getByLabelText("질문 입력") as HTMLTextAreaElement;
    expect(textarea.value).toBe(chipText);
    expect(textarea).toHaveFocus();
  });

  it("submits question and navigates to /ask route", () => {
    mockPush.mockClear();
    render(<AskHero workspaceId="ws-1" />);

    const textarea = screen.getByLabelText("질문 입력");
    fireEvent.change(textarea, { target: { value: "테넌트 격리 원칙" } });

    const submitBtn = screen.getByRole("button", { name: "질문하기" });
    fireEvent.click(submitBtn);

    expect(mockPush).toHaveBeenCalledWith(
      `/w/ws-1/ask?q=${encodeURIComponent("테넌트 격리 원칙").replace(/%20/g, "+")}`,
    );
  });

  it("opens scope menu on click, selects an option, and closes menu", () => {
    render(<AskHero workspaceId="ws-1" />);

    const trigger = screen.getByRole("button", { name: /워크스페이스 전체/ });
    expect(screen.queryByRole("menu")).not.toBeInTheDocument();

    fireEvent.click(trigger);
    expect(screen.getByRole("menu")).toBeInTheDocument();

    const categoryOption = screen.getByRole("menuitem", {
      name: /카테고리 한정/,
    });
    fireEvent.click(categoryOption);

    expect(screen.queryByRole("menu")).not.toBeInTheDocument();
    expect(screen.getByText("카테고리 한정")).toBeInTheDocument();
  });

  it("closes scope menu when clicking outside", () => {
    render(
      <div>
        <div data-testid="outside-area">외부 영역</div>
        <AskHero workspaceId="ws-1" />
      </div>,
    );

    const trigger = screen.getByRole("button", { name: /워크스페이스 전체/ });
    fireEvent.click(trigger);
    expect(screen.getByRole("menu")).toBeInTheDocument();

    fireEvent.mouseDown(screen.getByTestId("outside-area"));
    expect(screen.queryByRole("menu")).not.toBeInTheDocument();
  });

  it("⌘/Ctrl + Enter 로 질문을 제출한다", () => {
    mockPush.mockClear();
    render(<AskHero workspaceId="ws-1" />);

    const textarea = screen.getByLabelText("질문 입력");
    fireEvent.change(textarea, { target: { value: "테넌트 격리 원칙" } });
    fireEvent.keyDown(textarea, { key: "Enter", metaKey: true });

    expect(mockPush).toHaveBeenCalledWith(
      `/w/ws-1/ask?q=${encodeURIComponent("테넌트 격리 원칙").replace(/%20/g, "+")}`,
    );
  });
});

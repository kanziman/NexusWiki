import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

const mockPush = vi.hoisted(() => vi.fn());

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: mockPush,
  }),
}));

import { AskHero } from "@/components/AskHero";

describe("AskHero", () => {
  it("renders input, scope selector, submit button, and starter chips", () => {
    render(<AskHero workspaceId="ws-1" />);

    expect(screen.getByLabelText("질문 입력")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "질문하기" }),
    ).toBeInTheDocument();
    expect(screen.getByText("워크스페이스 전체")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "PostgreSQL RLS 격리 규칙 요약" }),
    ).toBeInTheDocument();
  });

  it("populates textarea when a starter chip is clicked", () => {
    render(<AskHero workspaceId="ws-1" />);

    const chip = screen.getByRole("button", {
      name: "PostgreSQL RLS 격리 규칙 요약",
    });
    fireEvent.click(chip);

    const textarea = screen.getByLabelText("질문 입력") as HTMLTextAreaElement;
    expect(textarea.value).toBe("PostgreSQL RLS 격리 규칙 요약");
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
});

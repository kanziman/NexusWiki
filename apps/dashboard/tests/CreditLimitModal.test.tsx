import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { CreditLimitModal } from "@/components/CreditLimitModal";

describe("CreditLimitModal", () => {
  it("renders modal content when open is true", () => {
    const onOpenChange = vi.fn();
    render(
      <CreditLimitModal
        open={true}
        onOpenChange={onOpenChange}
        workspaceId="ws-test"
      />,
    );

    expect(
      screen.getByText("이번 달 무료 크레딧을 모두 소진했습니다"),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/월간 무료 AI 질의 및 소스 분석 한도에 도달했습니다/),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /사용량 확인/ })).toHaveAttribute(
      "href",
      "/w/ws-test/settings?tab=operations",
    );
  });

  it("calls onOpenChange when close button is clicked", async () => {
    const user = userEvent.setup();
    const onOpenChange = vi.fn();
    render(<CreditLimitModal open={true} onOpenChange={onOpenChange} />);

    await user.click(screen.getByRole("button", { name: "창 닫기" }));
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });
});

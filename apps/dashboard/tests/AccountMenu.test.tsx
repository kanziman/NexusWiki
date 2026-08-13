import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const signOut = vi.fn();

vi.mock("@/lib/supabase/client", () => ({
  createClient: () => ({ auth: { signOut } }),
}));

import { AccountMenu } from "@/components/AccountMenu";

const assign = vi.fn();
const originalLocation = window.location;

describe("AccountMenu", () => {
  beforeEach(() => {
    signOut.mockReset();
    assign.mockReset();
    // @ts-expect-error - 테스트 전용 location 스텁 교체
    delete window.location;
    // @ts-expect-error - 테스트 전용 location 스텁 교체
    window.location = { ...originalLocation, assign };
  });

  afterEach(() => {
    // @ts-expect-error - 원래 location 복구
    window.location = originalLocation;
  });

  it("shows the minimal session identity and signs out from the account menu", async () => {
    const user = userEvent.setup();
    signOut.mockResolvedValue({ error: null });
    render(<AccountMenu email="member@example.com" />);

    await user.click(screen.getByRole("button", { name: "계정 메뉴" }));
    expect(screen.getByText("member@example.com")).toBeInTheDocument();
    await user.click(screen.getByRole("menuitem", { name: "로그아웃" }));

    await waitFor(() => expect(signOut).toHaveBeenCalledOnce());
    expect(assign).toHaveBeenCalledWith("/login");
  });

  it("supports keyboard activation and presents a retry-safe error", async () => {
    const user = userEvent.setup();
    signOut.mockResolvedValue({ error: { message: "network" } });
    render(<AccountMenu email="member@example.com" />);

    await user.tab();
    expect(screen.getByRole("button", { name: "계정 메뉴" })).toHaveFocus();
    await user.keyboard("{Enter}");
    await user.keyboard("{Enter}");

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "로그아웃하지 못했습니다. 다시 시도해주세요.",
    );
    expect(assign).not.toHaveBeenCalled();
  });
});

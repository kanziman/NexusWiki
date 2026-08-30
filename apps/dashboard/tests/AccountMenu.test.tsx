import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const signOut = vi.fn();
const apiFetch = vi.fn();

vi.mock("@/lib/supabase/client", () => ({
  createClient: () => ({ auth: { signOut } }),
}));

vi.mock("@/lib/api-client", () => ({
  apiFetch: (...args: unknown[]) => apiFetch(...args),
}));

import { AccountMenu } from "@/components/AccountMenu";

const assign = vi.fn();
const originalLocation = window.location;

describe("AccountMenu", () => {
  beforeEach(() => {
    signOut.mockReset();
    apiFetch.mockReset();
    apiFetch.mockResolvedValue({
      cap_micros: 1000000,
      spent_micros: 120000,
      remaining_micros: 880000,
      month_start: "2026-08-01T00:00:00Z",
      truncated: false,
      authoritative: false,
    });
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
    render(<AccountMenu email="member@example.com" workspaceId="ws-1" />);

    await user.tab();
    expect(screen.getByRole("button", { name: "계정 메뉴" })).toHaveFocus();
    await user.keyboard("{Enter}");

    expect(
      screen.getByRole("menuitem", { name: "워크스페이스 설정" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("menuitem", { name: "새 워크스페이스 만들기" }),
    ).toBeInTheDocument();

    await user.click(screen.getByRole("menuitem", { name: "로그아웃" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "로그아웃하지 못했습니다. 다시 시도해주세요.",
    );
    expect(assign).not.toHaveBeenCalled();
  });

  it("새 워크스페이스 만들기 메뉴 선택 시 생성 모달 다이얼로그를 연다", async () => {
    const user = userEvent.setup();
    render(<AccountMenu email="member@example.com" workspaceId="ws-1" />);

    await user.click(screen.getByRole("button", { name: "계정 메뉴" }));
    await user.click(
      screen.getByRole("menuitem", { name: "새 워크스페이스 만들기" }),
    );

    expect(
      await screen.findByRole("dialog", { name: "새 워크스페이스 만들기" }),
    ).toBeInTheDocument();
    expect(
      screen.getByPlaceholderText("예: 마케팅 전략 위키"),
    ).toBeInTheDocument();
  });

  it("보유 워크스페이스가 3개 이상이면 최대치 도달 안내를 모달에 표시한다", async () => {
    const user = userEvent.setup();
    render(
      <AccountMenu
        email="member@example.com"
        workspaceId="ws-1"
        workspaceCount={3}
      />,
    );

    await user.click(screen.getByRole("button", { name: "계정 메뉴" }));
    expect(screen.getByText("최대 3개")).toBeInTheDocument();

    await user.click(
      screen.getByRole("menuitem", { name: /새 워크스페이스 만들기/ }),
    );

    expect(
      await screen.findByText("워크스페이스 최대 개수(3개)에 도달했습니다"),
    ).toBeInTheDocument();
    expect(
      screen.queryByPlaceholderText("예: 마케팅 전략 위키"),
    ).not.toBeInTheDocument();
  });

  it("메뉴가 열렸을 때 워크스페이스의 잔여 무료 크레딧 카드를 렌더링한다", async () => {
    const user = userEvent.setup();
    render(<AccountMenu email="member@example.com" workspaceId="ws-1" />);

    await user.click(screen.getByRole("button", { name: "계정 메뉴" }));

    expect(await screen.findByText("무료 크레딧")).toBeInTheDocument();
    expect(screen.getByText("US$0.88 남음")).toBeInTheDocument();
    expect(screen.getByText("사용 US$0.12")).toBeInTheDocument();
    expect(screen.getByText("한도 US$1.00")).toBeInTheDocument();
  });
});

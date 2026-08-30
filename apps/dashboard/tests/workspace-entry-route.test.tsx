import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const state = vi.hoisted(() => ({
  user: { id: "user-1" } as { id: string } | null,
  workspaces: [] as { id: string; name: string }[],
  selectFields: "",
  orderField: "",
}));
const redirect = vi.hoisted(() =>
  vi.fn((destination: string) => {
    throw new Error(`redirect:${destination}`);
  }),
);

vi.mock("next/navigation", () => ({
  redirect,
  useRouter: () => ({ push: vi.fn() }),
}));
vi.mock("@/lib/supabase/server", () => ({
  createClient: vi.fn(async () => {
    const query = {
      select: (fields: string) => {
        state.selectFields = fields;
        return query;
      },
      order: async (field: string) => {
        state.orderField = field;
        return { data: state.workspaces, error: null };
      },
    };

    return {
      auth: { getUser: async () => ({ data: { user: state.user } }) },
      from: () => query,
    };
  }),
}));

import HomePage from "@/app/page";

describe("workspace entry route", () => {
  beforeEach(() => {
    redirect.mockClear();
    state.user = { id: "user-1" };
    state.workspaces = [];
    state.selectFields = "";
    state.orderField = "";
  });

  it("미인증 방문자(user = null)에게는 공개 랜딩 페이지를 표시한다", async () => {
    state.user = null;
    render(await HomePage());

    expect(
      screen.getByRole("heading", {
        name: /흩어진 영상과 문서를/i,
      }),
    ).toBeInTheDocument();
    expect(redirect).not.toHaveBeenCalled();
  });

  it("RLS가 빈 목록을 반환하면 personal 워크스페이스 온보딩을 표시한다", async () => {
    render(await HomePage());

    expect(
      screen.getByRole("heading", { name: "첫 워크스페이스 만들기" }),
    ).toBeInTheDocument();
    expect(redirect).not.toHaveBeenCalled();
  });

  it("redirects a user with one RLS-visible workspace to its URL-scoped home", async () => {
    state.workspaces = [{ id: "ws-1", name: "단일 워크스페이스" }];

    await expect(HomePage()).rejects.toThrow("redirect:/w/ws-1");

    expect(state.selectFields).toBe("id,name");
    expect(state.orderField).toBe("name");
  });

  it("renders only the RLS-visible workspaces as URL-scoped selection links", async () => {
    state.workspaces = [
      { id: "ws-1", name: "알파 워크스페이스" },
      { id: "ws-2", name: "베타 워크스페이스" },
    ];

    render(await HomePage());

    expect(
      screen.getByRole("heading", { name: "워크스페이스 선택" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "알파 워크스페이스" }),
    ).toHaveAttribute("href", "/w/ws-1");
    expect(
      screen.getByRole("link", { name: "베타 워크스페이스" }),
    ).toHaveAttribute("href", "/w/ws-2");
  });
});

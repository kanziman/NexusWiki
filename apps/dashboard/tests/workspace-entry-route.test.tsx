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

vi.mock("next/navigation", () => ({ redirect }));
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

  it("keeps invitation guidance when RLS exposes no workspace", async () => {
    render(await HomePage());

    expect(
      screen.getByText(
        "워크스페이스가 없습니다 — 관리자에게 초대를 요청하세요.",
      ),
    ).toBeInTheDocument();
    expect(redirect).not.toHaveBeenCalled();
  });

  it("redirects a user with one RLS-visible workspace to its URL-scoped home", async () => {
    state.workspaces = [{ id: "ws-1", name: "단일 프로젝트" }];

    await expect(HomePage()).rejects.toThrow("redirect:/w/ws-1");

    expect(state.selectFields).toBe("id,name");
    expect(state.orderField).toBe("name");
  });

  it("renders only the RLS-visible workspaces as URL-scoped selection links", async () => {
    state.workspaces = [
      { id: "ws-1", name: "알파 프로젝트" },
      { id: "ws-2", name: "베타 프로젝트" },
    ];

    render(await HomePage());

    expect(
      screen.getByRole("heading", { name: "프로젝트 선택" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "알파 프로젝트" })).toHaveAttribute(
      "href",
      "/w/ws-1",
    );
    expect(screen.getByRole("link", { name: "베타 프로젝트" })).toHaveAttribute(
      "href",
      "/w/ws-2",
    );
  });
});

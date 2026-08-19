import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const state = vi.hoisted(() => ({
  workspaces: [] as { id: string }[],
}));

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));
vi.mock("@/lib/supabase/server", () => ({
  createClient: async () => ({
    from: () => ({
      select: async () => ({ data: state.workspaces, error: null }),
    }),
  }),
}));

import NewWorkspacePage from "@/app/w/new/page";

describe("new workspace route", () => {
  beforeEach(() => {
    state.workspaces = [];
  });

  it("소속이 3개 미만이면 온보딩 생성 폼을 렌더링한다", async () => {
    state.workspaces = [{ id: "ws-1" }];

    render(await NewWorkspacePage());

    expect(
      screen.getByRole("heading", { name: "첫 워크스페이스 만들기" }),
    ).toBeInTheDocument();
  });

  it("소속이 3개면 상한 안내를 표시하고 폼을 렌더링하지 않는다", async () => {
    state.workspaces = [{ id: "ws-1" }, { id: "ws-2" }, { id: "ws-3" }];

    render(await NewWorkspacePage());

    expect(
      screen.getByRole("heading", {
        name: "워크스페이스는 최대 3개까지 만들 수 있습니다",
      }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "워크스페이스 만들기" }),
    ).not.toBeInTheDocument();
  });
});

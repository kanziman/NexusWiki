import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const state = vi.hoisted(() => ({
  sources: [] as { id: string; title: string; source_type: string }[],
  pages: [] as { id: string; title: string; slug: string }[],
}));

vi.mock("@/lib/supabase/server", () => ({
  createClient: vi.fn(async () => ({
    from: (table: string) => {
      const query = {
        select: () => query,
        eq: () => query,
        order: () => query,
        limit: async () => ({
          data: table === "raw_sources" ? state.sources : state.pages,
        }),
        single: async () => ({ data: { name: "내 프로젝트" } }),
      };
      return query;
    },
  })),
}));

import WorkspaceHomePage from "@/app/w/[workspaceId]/page";

describe("WorkspaceHomePage", () => {
  beforeEach(() => {
    state.sources = [];
    state.pages = [];
  });

  it("guides an empty workspace to add its first source", async () => {
    render(
      await WorkspaceHomePage({
        params: Promise.resolve({ workspaceId: "ws-1" }),
      }),
    );
    expect(screen.getByText("첫 자료를 등록하세요")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "자료 추가" })).toHaveAttribute(
      "href",
      "/w/ws-1/sources",
    );
  });

  it("shows only the active workspace recent activity", async () => {
    state.sources = [
      { id: "source-1", title: "요구사항", source_type: "file" },
    ];
    state.pages = [{ id: "page-1", title: "개요", slug: "overview" }];
    render(
      await WorkspaceHomePage({
        params: Promise.resolve({ workspaceId: "ws-1" }),
      }),
    );
    expect(screen.getByText("요구사항")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /개요/ })).toHaveAttribute(
      "href",
      "/w/ws-1/wiki/overview",
    );
  });
});

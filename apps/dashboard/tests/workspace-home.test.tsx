import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const state = vi.hoisted(() => ({
  sources: [] as {
    id: string;
    title: string;
    source_type: string;
    created_at: string;
  }[],
  pages: [] as {
    id: string;
    title: string;
    slug: string;
    category?: string;
    verification_status?: string;
    sources?: string[];
    updated_at: string;
  }[],
  links: [] as { target_slug: string; resolved: boolean }[],
}));

vi.mock("@/lib/supabase/server", () => ({
  createClient: vi.fn(async () => ({
    from: (table: string) => {
      const query = {
        select: () => query,
        eq: () => query,
        order: () => query,
        then: (resolve: (data: unknown) => unknown) => {
          if (table === "raw_sources") return resolve({ data: state.sources });
          if (table === "wiki_pages") return resolve({ data: state.pages });
          if (table === "wiki_links") return resolve({ data: state.links });
          return resolve({ data: [] });
        },
        single: async () => ({ data: { name: "내 워크스페이스" } }),
      };
      return query;
    },
  })),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => "/w/ws-1",
  useSearchParams: () => ({ get: () => null }),
}));

import WorkspaceHomePage from "@/app/w/[workspaceId]/page";

describe("WorkspaceHomePage", () => {
  beforeEach(() => {
    state.sources = [];
    state.pages = [];
    state.links = [];
  });

  it("renders workspace stats and empty state guidance when empty", async () => {
    render(
      await WorkspaceHomePage({
        params: Promise.resolve({ workspaceId: "ws-1" }),
      }),
    );
    expect(screen.getByText("내 워크스페이스")).toBeInTheDocument();
    expect(screen.getByText("컴파일된 문서")).toBeInTheDocument();
    expect(screen.getByText("연결된 원문 소스")).toBeInTheDocument();
    expect(screen.getByText("작성 대기 항목")).toBeInTheDocument();
    expect(
      screen.getByText("컴파일된 위키 문서가 아직 없습니다."),
    ).toBeInTheDocument();
  });

  it("shows active workspace wiki pages and backlog items", async () => {
    state.sources = [
      {
        id: "source-1",
        title: "요구사항",
        source_type: "file",
        created_at: new Date().toISOString(),
      },
    ];
    state.pages = [
      {
        id: "page-1",
        title: "개요 문서",
        slug: "overview",
        category: "concepts",
        verification_status: "verified",
        sources: ["source-1"],
        updated_at: new Date().toISOString(),
      },
    ];
    state.links = [{ target_slug: "missing-concept", resolved: false }];

    render(
      await WorkspaceHomePage({
        params: Promise.resolve({ workspaceId: "ws-1" }),
      }),
    );

    expect(screen.getByText("개요 문서")).toBeInTheDocument();
    expect(screen.getByText("검증 완료")).toBeInTheDocument();
    expect(screen.getByText("missing-concept")).toBeInTheDocument();
    expect(screen.getByText(/위키 1곳에서 인용됨/)).toBeInTheDocument();
  });
});

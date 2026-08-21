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
    disputed?: boolean;
    expires_at?: string | null;
    sources?: string[];
    updated_at: string;
  }[],
  links: [] as { target_slug: string; resolved: boolean }[],
  // ⚠️ 이 화면이 wiki_pages 에서 실제로 요청한 컬럼 목록. 예전 모의는 select()
  // 인자를 통째로 버려서, 신뢰 상태 컬럼을 빼먹어도 테스트가 전부 통과했다 —
  // disputed 누락이 그렇게 리뷰까지 살아남았다. 발화 지점을 직접 지킨다.
  wikiSelect: "",
}));

vi.mock("@/lib/supabase/server", () => ({
  createClient: vi.fn(async () => ({
    from: (table: string) => {
      const query = {
        select: (columns?: string) => {
          if (table === "wiki_pages" && typeof columns === "string") {
            state.wikiSelect = columns;
          }
          return query;
        },
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
    expect(screen.getByText("검증됨")).toBeInTheDocument();
    expect(screen.getByText("missing-concept")).toBeInTheDocument();
    expect(screen.getByText(/위키 1곳에서 인용됨/)).toBeInTheDocument();
  });

  // ⚠️ 회귀 방지. 신뢰 상태를 판정하는 컬럼을 select 에서 빼먹으면 화면은
  // 예외 없이 "검증됨"으로 그려진다 — 조용히 신뢰를 실제보다 높게 보이게
  // 하는 부류라 렌더 단언만으로는 잡히지 않는다. 실제로 disputed 가 이렇게
  // 누락됐고, expires_at 도 같은 구조로 빠져 있었다.
  it("위키 조회가 신뢰 상태 판정에 필요한 컬럼을 모두 요청한다", async () => {
    state.pages = [];
    state.links = [];

    render(
      await WorkspaceHomePage({
        params: Promise.resolve({ workspaceId: "ws-1" }),
      }),
    );

    for (const column of ["verification_status", "disputed", "expires_at"]) {
      expect(state.wikiSelect.split(",")).toContain(column);
    }
  });

  // ⚠️ select 만 지키면 절반이다. 컬럼을 읽어와도 select→props 매핑에서
  // `disputed: p.disputed` 를 지우면 화면은 다시 조용히 "검증됨"이 된다 —
  // 타입은 optional 이라 통과하고 select 가드도 통과한다. 렌더 결과를
  // 단언해 그 마지막 한 겹까지 덮는다.
  it("충돌·만료 문서가 홈에서 검증됨으로 표시되지 않는다", async () => {
    state.pages = [
      {
        id: "p-disputed",
        title: "충돌 문서",
        slug: "disputed-doc",
        category: "concepts",
        verification_status: "verified",
        disputed: true,
        updated_at: "2026-08-20T00:00:00Z",
      },
      {
        id: "p-expired",
        title: "만료 문서",
        slug: "expired-doc",
        category: "concepts",
        verification_status: "verified",
        expires_at: "2020-01-01T00:00:00Z",
        updated_at: "2026-08-20T00:00:00Z",
      },
    ];
    state.links = [];

    render(
      await WorkspaceHomePage({
        params: Promise.resolve({ workspaceId: "ws-1" }),
      }),
    );

    expect(screen.getByText("충돌 감지")).toBeInTheDocument();
    expect(screen.getByText("검증 만료됨")).toBeInTheDocument();
    expect(screen.queryByText("검증됨")).toBeNull();
  });
});

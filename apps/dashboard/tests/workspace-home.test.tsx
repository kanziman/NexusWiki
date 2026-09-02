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
  chunks: [] as { id: string }[],
  // undefined 면 chunks.length 로 채운다. 명시적 숫자/null 은 count 헤더를
  // 행 배열과 어긋나게 만들어, 다시 data.length 로 세면 테스트가 깨지게 한다.
  chunkCount: undefined as number | null | undefined,
  chunkError: null as { message: string } | null,
  // ⚠️ 이 화면이 wiki_pages 에서 실제로 요청한 컬럼 목록. 예전 모의는 select()
  // 인자를 통째로 버려서, 신뢰 상태 컬럼을 빼먹어도 테스트가 전부 통과했다 —
  // disputed 누락이 그렇게 리뷰까지 살아남았다. 발화 지점을 직접 지킨다.
  wikiSelect: "",
  chunkSelect: "",
  chunkSelectOptions: null as { count?: string; head?: boolean } | null,
  chunkWorkspaceId: "",
}));

vi.mock("@/lib/supabase/server", () => ({
  createClient: vi.fn(async () => ({
    from: (table: string) => {
      const query = {
        select: (
          columns?: string,
          options?: { count?: string; head?: boolean },
        ) => {
          if (table === "wiki_pages" && typeof columns === "string") {
            state.wikiSelect = columns;
          }
          if (table === "source_chunks") {
            state.chunkSelect = typeof columns === "string" ? columns : "";
            state.chunkSelectOptions = options ?? null;
          }
          return query;
        },
        eq: (column?: string, value?: string) => {
          if (
            table === "source_chunks" &&
            column === "workspace_id" &&
            typeof value === "string"
          ) {
            state.chunkWorkspaceId = value;
          }
          return query;
        },
        order: () => query,
        then: (resolve: (data: unknown) => unknown) => {
          if (table === "raw_sources") return resolve({ data: state.sources });
          if (table === "wiki_pages") return resolve({ data: state.pages });
          if (table === "wiki_links") return resolve({ data: state.links });
          if (table === "source_chunks") {
            if (state.chunkError) {
              return resolve({
                data: null,
                count: null,
                error: state.chunkError,
              });
            }
            const count =
              state.chunkCount !== undefined
                ? state.chunkCount
                : state.chunks.length;
            // head: true 는 행을 돌려주지 않는다. 옵션이 빠지면 행 배열이
            // 그대로 나가 data.length 회귀를 드러낸다.
            return resolve({
              data: state.chunkSelectOptions?.head ? [] : state.chunks,
              count,
              error: null,
            });
          }
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
    state.chunks = [];
    state.chunkCount = undefined;
    state.chunkError = null;
    state.chunkSelect = "";
    state.chunkSelectOptions = null;
    state.chunkWorkspaceId = "";
  });

  it("renders workspace stats and empty state guidance when empty", async () => {
    render(
      await WorkspaceHomePage({
        params: Promise.resolve({ workspaceId: "ws-1" }),
      }),
    );
    expect(
      screen.getByRole("heading", { level: 1, name: "홈 대시보드" }),
    ).toBeInTheDocument();
    expect(screen.getByText("지식 완결도 0%")).toBeInTheDocument();
    expect(
      screen.getByText(/연결된 원문 0개와 컴파일된 위키 0개/),
    ).toBeInTheDocument();
    expect(screen.getByText("컴파일된 위키")).toBeInTheDocument();
    expect(screen.getByText("연결된 원문 소스")).toBeInTheDocument();
    expect(screen.getByText("작성 대기 지식 공백")).toBeInTheDocument();
    expect(screen.getByText("최종 업데이트")).toBeInTheDocument();
    expect(screen.getByText("인덱싱된 청크 0개")).toBeInTheDocument();
    expect(state.chunkSelect).toBe("id");
    expect(state.chunkSelectOptions).toEqual({
      count: "exact",
      head: true,
    });
    expect(screen.queryByText(/라이브/)).toBeNull();
    expect(
      screen.getByText("컴파일된 위키 문서가 아직 없습니다."),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "PostgreSQL RLS 격리 규칙 요약" }),
    ).not.toBeInTheDocument();
    expect(state.chunkWorkspaceId).toBe("ws-1");
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
    state.chunks = [{ id: "chunk-1" }, { id: "chunk-2" }];

    render(
      await WorkspaceHomePage({
        params: Promise.resolve({ workspaceId: "ws-1" }),
      }),
    );

    expect(screen.getByRole("link", { name: /개요 문서/ })).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "개요 문서" }),
    ).toBeInTheDocument();
    expect(screen.getByText("검증됨")).toBeInTheDocument();
    expect(screen.getByText("지식 완결도 100%")).toBeInTheDocument();
    expect(screen.getByText("검증률 100%")).toBeInTheDocument();
    expect(screen.getByText("인덱싱된 청크 2개")).toBeInTheDocument();
    expect(screen.getByText("missing-concept")).toBeInTheDocument();
    expect(screen.getByText(/위키 1곳에서 인용됨/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "소스 추가" })).toHaveAttribute(
      "href",
      "/w/ws-1/sources?prefillTitle=missing-concept&tab=text",
    );
    expect(state.chunkWorkspaceId).toBe("ws-1");
  });

  it("추천 칩은 인용 빈도 상위 4개 위키 제목이며 하드코딩 질문을 쓰지 않는다", async () => {
    state.pages = [
      {
        id: "p1",
        title: "인용 1위",
        slug: "c1",
        category: "concepts",
        verification_status: "verified",
        sources: ["a", "b", "c", "d", "e"],
        updated_at: "2026-08-20T00:00:00Z",
      },
      {
        id: "p2",
        title: "인용 2위",
        slug: "c2",
        category: "concepts",
        verification_status: "verified",
        sources: ["a", "b", "c", "d"],
        updated_at: "2026-08-20T00:00:00Z",
      },
      {
        id: "p3",
        title: "인용 3위",
        slug: "c3",
        category: "guides",
        verification_status: "unverified",
        sources: ["a", "b", "c"],
        updated_at: "2026-08-20T00:00:00Z",
      },
      {
        id: "p4",
        title: "인용 4위",
        slug: "c4",
        category: "maps",
        verification_status: "unverified",
        sources: ["a", "b"],
        updated_at: "2026-08-20T00:00:00Z",
      },
      {
        id: "p5",
        title: "인용 5위",
        slug: "c5",
        category: "entities",
        verification_status: "unverified",
        sources: ["a"],
        updated_at: "2026-08-20T00:00:00Z",
      },
    ];

    render(
      await WorkspaceHomePage({
        params: Promise.resolve({ workspaceId: "ws-1" }),
      }),
    );

    expect(
      screen.getByRole("button", { name: "인용 1위" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "인용 2위" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "인용 3위" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "인용 4위" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "인용 5위" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "PostgreSQL RLS 격리 규칙 요약" }),
    ).not.toBeInTheDocument();
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
    expect(screen.getByText("지식 완결도 0%")).toBeInTheDocument();
    expect(screen.getByText("검증률 0%")).toBeInTheDocument();
  });

  // ⚠️ 행을 받아 .length 로 세면 PostgREST max_rows=1000 에서 조용히 잘린다.
  // 모의는 행 1000개와 count 2500을 동시에 주고, head: true 일 때만 행을
  // 비운다 — 다시 배열 길이로 돌아가면 2500이 아니라 0 또는 1000이 된다.
  it("청크 수는 count 헤더에서 읽고 행 배열 길이를 쓰지 않는다", async () => {
    state.chunks = Array.from({ length: 1000 }, (_, index) => ({
      id: `chunk-${index}`,
    }));
    state.chunkCount = 2500;

    render(
      await WorkspaceHomePage({
        params: Promise.resolve({ workspaceId: "ws-1" }),
      }),
    );

    expect(screen.getByText("인덱싱된 청크 2500개")).toBeInTheDocument();
    expect(screen.queryByText("인덱싱된 청크 1000개")).not.toBeInTheDocument();
    expect(screen.queryByText("인덱싱된 청크 0개")).not.toBeInTheDocument();
    expect(state.chunkSelect).toBe("id");
    expect(state.chunkSelectOptions).toEqual({
      count: "exact",
      head: true,
    });
    expect(state.chunkWorkspaceId).toBe("ws-1");
  });

  it("청크 조회가 실패하면 0개로 위장하지 않는다", async () => {
    const errorSpy = vi
      .spyOn(console, "error")
      .mockImplementation(() => undefined);
    state.chunks = [{ id: "chunk-1" }];
    state.chunkError = { message: "source_chunks timed out" };

    try {
      render(
        await WorkspaceHomePage({
          params: Promise.resolve({ workspaceId: "ws-1" }),
        }),
      );

      expect(screen.queryByText("인덱싱된 청크 0개")).not.toBeInTheDocument();
      expect(screen.queryByText("인덱싱된 청크 1개")).not.toBeInTheDocument();
      expect(screen.getByText("인덱싱된 청크 —")).toBeInTheDocument();
      expect(errorSpy).toHaveBeenCalled();
      expect(state.chunkWorkspaceId).toBe("ws-1");
    } finally {
      errorSpy.mockRestore();
    }
  });

  it("청크 count 가 없으면 0개로 위장하지 않는다", async () => {
    state.chunks = [{ id: "chunk-1" }];
    state.chunkCount = null;

    render(
      await WorkspaceHomePage({
        params: Promise.resolve({ workspaceId: "ws-1" }),
      }),
    );

    expect(screen.queryByText("인덱싱된 청크 0개")).not.toBeInTheDocument();
    expect(screen.queryByText("인덱싱된 청크 1개")).not.toBeInTheDocument();
    expect(screen.getByText("인덱싱된 청크 —")).toBeInTheDocument();
    expect(state.chunkWorkspaceId).toBe("ws-1");
  });
});

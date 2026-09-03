import { beforeEach, describe, expect, it, vi } from "vitest";

import { baseSlug } from "@/lib/wiki-links";

// add-backlog-topic-context 1.2: 본문 조회는 미해결 링크의 from_wiki_id 집합으로
// 제한된다. 이 상태로 `wiki_pages`(content 컬럼) 조회에 실제로 넘어간 `.in()`
// id 목록을 기록해, "결손이 있는 문서로만 제한" 계약을 직접 관측한다.
const state = vi.hoisted(() => ({
  contentInCalls: [] as string[][],
}));

const fixtures = vi.hoisted(() => ({
  links: [] as {
    id: string;
    target_slug: string;
    from_wiki_id: string | null;
    created_at: string;
  }[],
  pages: [] as { id: string; slug: string; title: string }[],
  contents: {} as Record<string, string>,
  linksError: null as { message: string } | null,
  pagesError: null as { message: string } | null,
}));

vi.mock("@/lib/supabase/server", () => ({
  createClient: vi.fn(async () => ({
    from: (table: string) => {
      let columns = "";
      let inIds: string[] = [];
      const query = {
        select: (cols: string) => {
          columns = cols;
          return query;
        },
        eq: () => query,
        is: () => query,
        in: (_column: string, ids: string[]) => {
          inIds = ids;
          if (table === "wiki_pages" && columns.includes("content")) {
            state.contentInCalls.push(ids);
          }
          return query;
        },
        then: (
          resolve: (value: {
            data: unknown;
            error: { message: string } | null;
          }) => unknown,
        ) => {
          if (table === "wiki_links") {
            return resolve({
              data: fixtures.linksError ? null : fixtures.links,
              error: fixtures.linksError,
            });
          }
          if (table === "wiki_pages" && columns.includes("content")) {
            const rows = inIds
              .filter((id) => id in fixtures.contents)
              .map((id) => ({ id, content: fixtures.contents[id] }));
            return resolve({ data: rows, error: null });
          }
          if (table === "wiki_pages") {
            return resolve({
              data: fixtures.pagesError ? null : fixtures.pages,
              error: fixtures.pagesError,
            });
          }
          return resolve({ data: [], error: null });
        },
      };
      return query;
    },
  })),
}));

vi.mock("@/components/BacklogList", () => ({
  BacklogList: () => null,
}));

import { BacklogList } from "@/components/BacklogList";
import BacklogPage from "@/app/w/[workspaceId]/backlog/page";

type RenderedProps = {
  workspaceId: string;
  initialItems: {
    target_slug: string;
    display_title: string;
    impact: number;
    referencing_pages: {
      id: string;
      slug: string;
      title: string;
      excerpt: string | null;
    }[];
  }[];
  loadFailed?: boolean;
};

async function renderBacklogPage(): Promise<RenderedProps> {
  const result = await BacklogPage({
    params: Promise.resolve({ workspaceId: "workspace-1" }),
  });
  expect(result.type).toBe(BacklogList);
  return result.props as RenderedProps;
}

describe("BacklogPage route", () => {
  beforeEach(() => {
    state.contentInCalls = [];
    fixtures.links = [];
    fixtures.pages = [];
    fixtures.contents = {};
    fixtures.linksError = null;
    fixtures.pagesError = null;
  });

  it("본문 조회를 미해결 링크가 실제로 가리키는 from_wiki_id 집합으로 제한한다", async () => {
    fixtures.links = [
      {
        id: "l1",
        target_slug: "rls-정책v2",
        from_wiki_id: "wiki-a",
        created_at: "2026-08-15T00:00:00Z",
      },
    ];
    // wiki-b 는 어떤 미해결 링크의 출발지도 아니다 — 조회 범위에 들면 안 된다.
    fixtures.pages = [
      { id: "wiki-a", slug: "arch-guide", title: "아키텍처 가이드" },
      { id: "wiki-b", slug: "unrelated", title: "무관한 문서" },
    ];
    fixtures.contents = { "wiki-a": "본문 [[RLS 정책(v2)]] 계속" };

    await renderBacklogPage();

    expect(state.contentInCalls).toHaveLength(1);
    expect(state.contentInCalls[0]).toEqual(["wiki-a"]);
  });

  it("백로그가 비어 있으면 본문 조회 자체가 발생하지 않는다", async () => {
    fixtures.links = [];
    fixtures.pages = [
      { id: "wiki-a", slug: "arch-guide", title: "아키텍처 가이드" },
    ];

    const props = await renderBacklogPage();

    expect(state.contentInCalls).toHaveLength(0);
    expect(props.loadFailed).toBe(false);
  });

  it("미해결 링크 조회가 운영 오류를 반환하면 빈 결과와 구분되는 loadFailed 를 전달한다", async () => {
    fixtures.linksError = { message: "connection reset" };
    fixtures.pages = [
      { id: "wiki-a", slug: "arch-guide", title: "아키텍처 가이드" },
    ];

    const props = await renderBacklogPage();

    expect(props.loadFailed).toBe(true);
    // 실패한 조회 결과를 빈 배열인 척 넘기지 않는다 — items 는 비어 있을
    // 수 있지만 loadFailed 로만 "실패"와 "정상 빈 상태"가 구분된다.
    expect(props.initialItems).toEqual([]);
  });

  it("위키 페이지 메타데이터 조회가 실패해도 loadFailed 를 전달한다", async () => {
    fixtures.links = [
      {
        id: "l1",
        target_slug: "캐시-계층-전략",
        from_wiki_id: "wiki-a",
        created_at: "2026-08-15T00:00:00Z",
      },
    ];
    fixtures.pagesError = { message: "boom" };

    const props = await renderBacklogPage();

    expect(props.loadFailed).toBe(true);
  });

  it("행 라벨이 인용 문서 본문에서 복원한 [[표기]]를 쓴다", async () => {
    fixtures.links = [
      {
        id: "l1",
        target_slug: baseSlug("RLS 정책(v2)"),
        from_wiki_id: "wiki-a",
        created_at: "2026-08-15T00:00:00Z",
      },
    ];
    fixtures.pages = [
      { id: "wiki-a", slug: "arch-guide", title: "아키텍처 가이드" },
    ];
    fixtures.contents = { "wiki-a": "본문 [[RLS 정책(v2)]] 계속" };

    const props = await renderBacklogPage();

    expect(props.initialItems[0].display_title).toBe("RLS 정책(v2)");
    expect(props.initialItems[0].target_slug).toBe(baseSlug("RLS 정책(v2)"));
  });

  it("인용 문서들이 서로 다르게 표기하면 최빈 표기를 쓰고, 동수면 위키 제목 오름차순 첫 문서를 따른다", async () => {
    const slug = baseSlug("캐시 계층 전략");
    fixtures.links = [
      {
        id: "l1",
        target_slug: slug,
        from_wiki_id: "wiki-a",
        created_at: "2026-08-15T00:00:00Z",
      },
      {
        id: "l2",
        target_slug: slug,
        from_wiki_id: "wiki-b",
        created_at: "2026-08-16T00:00:00Z",
      },
      {
        id: "l3",
        target_slug: slug,
        from_wiki_id: "wiki-c",
        created_at: "2026-08-17T00:00:00Z",
      },
    ];
    // 제목 오름차순: "가나다" < "나다라" < "다라마"
    fixtures.pages = [
      { id: "wiki-a", slug: "a", title: "가나다" },
      { id: "wiki-b", slug: "b", title: "나다라" },
      { id: "wiki-c", slug: "c", title: "다라마" },
    ];
    fixtures.contents = {
      "wiki-a": "[[캐시 계층 전략]]",
      "wiki-b": "[[캐시 계층전략]]",
      "wiki-c": "[[캐시 계층 전략]]",
    };

    const props = await renderBacklogPage();

    // "캐시 계층 전략" 2회 vs "캐시 계층전략" 1회 — 최빈값이 이긴다.
    expect(props.initialItems[0].display_title).toBe("캐시 계층 전략");
  });

  it("동수 표기는 위키 제목이 앞선 문서의 표기를 따른다", async () => {
    // casefold는 정규화 과정에 포함되지만 표기 자체의 대소문자는 보존된다 —
    // "Auth Flow"와 "AUTH FLOW"는 같은 target_slug로 슬러그화되는 서로 다른
    // 표기다. 각각 한 문서에서만 등장하므로 빈도는 동수 1:1이다.
    const slug = baseSlug("Auth Flow");
    fixtures.links = [
      {
        id: "l1",
        target_slug: slug,
        from_wiki_id: "wiki-a",
        created_at: "2026-08-15T00:00:00Z",
      },
      {
        id: "l2",
        target_slug: slug,
        from_wiki_id: "wiki-b",
        created_at: "2026-08-16T00:00:00Z",
      },
    ];
    // 제목 오름차순: "가이드" < "나중문서" — wiki-a 가 먼저다.
    fixtures.pages = [
      { id: "wiki-a", slug: "a", title: "가이드" },
      { id: "wiki-b", slug: "b", title: "나중문서" },
    ];
    fixtures.contents = {
      "wiki-a": "[[Auth Flow]]",
      "wiki-b": "[[AUTH FLOW]]",
    };

    const props = await renderBacklogPage();

    expect(props.initialItems[0].display_title).toBe("Auth Flow");
  });

  it("어느 본문에서도 표기를 찾지 못하면 target_slug 역변환으로 폴백한다", async () => {
    fixtures.links = [
      {
        id: "l1",
        target_slug: "아직-작성-안된-주제",
        from_wiki_id: "wiki-a",
        created_at: "2026-08-15T00:00:00Z",
      },
    ];
    fixtures.pages = [
      { id: "wiki-a", slug: "arch-guide", title: "아키텍처 가이드" },
    ];
    // 본문에 이 주제로 슬러그화되는 [[...]]가 없다.
    fixtures.contents = { "wiki-a": "이 문서는 다른 내용만 담고 있다." };

    const props = await renderBacklogPage();

    expect(props.initialItems[0].display_title).toBe("아직 작성 안된 주제");
  });

  it("인용 문서마다 링크 주변 인용 문맥 발췌를 붙인다 (3.1)", async () => {
    fixtures.links = [
      {
        id: "l1",
        target_slug: baseSlug("캐시 계층 전략"),
        from_wiki_id: "wiki-a",
        created_at: "2026-08-15T00:00:00Z",
      },
    ];
    fixtures.pages = [
      { id: "wiki-a", slug: "arch-guide", title: "아키텍처 가이드" },
    ];
    fixtures.contents = {
      "wiki-a": "읽기 경로는 [[캐시 계층 전략]]을 따라 조회한다.",
    };

    const props = await renderBacklogPage();

    const [page] = props.initialItems[0].referencing_pages;
    expect(page.excerpt).not.toBeNull();
    expect(page.excerpt).toContain("캐시 계층 전략");
    // 서버가 만든 발췌에는 브래킷이 남지 않는다.
    expect(page.excerpt).not.toContain("[[");
  });

  it("본문에서 이 주제를 찾지 못한 인용 문서는 excerpt가 null이다", async () => {
    fixtures.links = [
      {
        id: "l1",
        target_slug: "아직-작성-안된-주제",
        from_wiki_id: "wiki-a",
        created_at: "2026-08-15T00:00:00Z",
      },
    ];
    fixtures.pages = [
      { id: "wiki-a", slug: "arch-guide", title: "아키텍처 가이드" },
    ];
    fixtures.contents = { "wiki-a": "이 문서는 다른 내용만 담고 있다." };

    const props = await renderBacklogPage();

    expect(props.initialItems[0].referencing_pages[0].excerpt).toBeNull();
  });

  it("위키 본문 전문을 클라이언트 props로 넘기지 않는다 — 계산된 문자열만 나간다", async () => {
    fixtures.links = [
      {
        id: "l1",
        target_slug: baseSlug("캐시 계층 전략"),
        from_wiki_id: "wiki-a",
        created_at: "2026-08-15T00:00:00Z",
      },
    ];
    fixtures.pages = [
      { id: "wiki-a", slug: "arch-guide", title: "아키텍처 가이드" },
    ];
    const fullBody =
      "이 문서는 매우 긴 본문이다. ".repeat(50) + "[[캐시 계층 전략]]";
    fixtures.contents = { "wiki-a": fullBody };

    const props = await renderBacklogPage();

    const serialized = JSON.stringify(props);
    // 발췌는 window 로 잘려 있으므로 원문 전체가 그대로 실려 있으면 안 된다.
    expect(serialized).not.toContain(fullBody);
    expect(serialized).not.toContain("content");
  });
});

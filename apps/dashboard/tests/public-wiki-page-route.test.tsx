import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

const notFoundMock = vi.fn();
vi.mock("next/navigation", () => ({
  notFound: () => {
    notFoundMock();
    throw new Error("NEXT_NOT_FOUND");
  },
}));

type MockSettings = {
  workspace_id: string;
  workspace_slug: string;
  allow_public_sharing: boolean;
  public_display_name: string | null;
  public_description: string | null;
};

type MockPub = {
  published_slug: string;
  published_title: string;
  published_content: string;
  published_citations: {
    anchor: string;
    source_title: string;
    snippet: string;
  }[];
  published_at: string;
};

let mockSettings: MockSettings | null = null;
let mockPublications: MockPub[] = [];

// ⚠️ 세션 클라이언트가 쓰이면 즉시 실패해야 한다 — 이 회귀가 정확히
// "테스트는 통과하는데 킬스위치만 조용히 무력화되는" 형태였다.
const sessionClient = vi.fn();
vi.mock("@/lib/supabase/server", () => ({
  createClient: (...args: unknown[]) => {
    sessionClient(...args);
    throw new Error("공개 라우트가 요청자 세션 클라이언트를 사용했다");
  },
}));

vi.mock("@/lib/supabase/public", () => ({
  createPublicClient: vi.fn(() => ({
    from: (table: string) => {
      const query = {
        select: () => query,
        eq: () => query,
        order: () => query,
        maybeSingle: async () => ({
          data: table === "workspace_public_settings" ? mockSettings : null,
          error: null,
        }),
        then(resolve: (value: { data: unknown; error: null }) => void) {
          resolve({
            data: table === "wiki_page_publications" ? mockPublications : [],
            error: null,
          });
        },
      };
      return query;
    },
  })),
}));

import PublicWikiPage from "@/app/p/[slug]/[page]/page";

describe("PublicWikiPage route", () => {
  it("세션 쿠키를 싣지 않는 anon 클라이언트로만 조회한다", async () => {
    mockSettings = {
      workspace_id: "ws-1",
      workspace_slug: "engineering",
      allow_public_sharing: true,
      public_display_name: "엔지니어링 팀",
      public_description: null,
    };
    mockPublications = [
      {
        published_slug: "cache-strategy",
        published_title: "캐시 계층 전략",
        published_content: "본문",
        published_citations: [],
        published_at: "2026-08-17T00:00:00Z",
      },
    ];

    await PublicWikiPage({
      params: Promise.resolve({ slug: "engineering", page: "cache-strategy" }),
    });

    // 0016 의 *_select_member 정책은 킬스위치를 보지 않는다. authenticated 로
    // 실행하는 순간 멤버에게는 킬스위치가 꺼진 페이지도 렌더링된다.
    expect(sessionClient).not.toHaveBeenCalled();
  });

  it("calls notFound when public sharing is not enabled or workspace is not found", async () => {
    mockSettings = null;
    mockPublications = [];

    await expect(
      PublicWikiPage({
        params: Promise.resolve({
          slug: "engineering",
          page: "cache-strategy",
        }),
      }),
    ).rejects.toThrow("NEXT_NOT_FOUND");

    expect(notFoundMock).toHaveBeenCalled();
  });

  it("renders published document and citations when public sharing is active", async () => {
    mockSettings = {
      workspace_id: "ws-1",
      workspace_slug: "engineering",
      allow_public_sharing: true,
      public_display_name: "엔지니어링 팀",
      public_description: "엔지니어링 지식 베이스",
    };

    mockPublications = [
      {
        published_slug: "cache-strategy",
        published_title: "캐시 계층 전략",
        published_content: "이 문서는 분산 캐시 설계 가이드입니다.",
        published_citations: [
          {
            anchor: "src:s1",
            source_title: "Redis 백서",
            snippet: "Redis는 인메모리 데이터 구조 저장소입니다.",
          },
        ],
        published_at: "2026-08-17T00:00:00Z",
      },
    ];

    const element = await PublicWikiPage({
      params: Promise.resolve({ slug: "engineering", page: "cache-strategy" }),
    });

    render(element);

    expect(screen.getAllByText("엔지니어링 팀").length).toBeGreaterThanOrEqual(
      1,
    );
    expect(screen.getAllByText("캐시 계층 전략").length).toBeGreaterThanOrEqual(
      1,
    );
    expect(
      screen.getByText("이 문서는 분산 캐시 설계 가이드입니다."),
    ).toBeInTheDocument();
    expect(screen.getByText("Redis 백서")).toBeInTheDocument();
    expect(
      screen.getByText(/"Redis는 인메모리 데이터 구조 저장소입니다."/),
    ).toBeInTheDocument();
  });

  it("발행 본문의 위키 링크 표기를 평문으로 펼치고 내부 라우트를 노출하지 않는다", async () => {
    mockSettings = {
      workspace_id: "ws-1",
      workspace_slug: "engineering",
      allow_public_sharing: true,
      public_display_name: "엔지니어링 팀",
      public_description: null,
    };

    mockPublications = [
      {
        published_slug: "cache-strategy",
        published_title: "캐시 계층 전략",
        // 발행본은 내부 본문의 스냅샷이라 [[...]] 표기가 그대로 들어 있다.
        published_content:
          "# 개요\n자세한 내용은 [[테넌트 격리 스파인]]을 보세요.",
        published_citations: [],
        published_at: "2026-08-17T00:00:00Z",
      },
    ];

    const element = await PublicWikiPage({
      params: Promise.resolve({ slug: "engineering", page: "cache-strategy" }),
    });

    const { container } = render(element);

    // 브래킷이 외부 열람자에게 보이면 내부 마크업이 새는 것이다.
    expect(container.textContent).not.toContain("[[");
    expect(container.textContent).not.toContain("]]");
    expect(screen.getByText(/테넌트 격리 스파인/)).toBeInTheDocument();

    // anon 이 도달할 수 없는 내부 라우트를 링크로 그리면 워크스페이스 식별자가
    // 함께 새어 나간다 — 공개 페이지에는 /w/ 링크가 하나도 없어야 한다.
    const internalLinks = container.querySelectorAll('a[href^="/w/"]');
    expect(internalLinks).toHaveLength(0);
  });

  it("renders lists and emphasis like the internal reader and hides related-doc markdown", async () => {
    mockSettings = {
      workspace_id: "ws-1",
      workspace_slug: "engineering",
      allow_public_sharing: true,
      public_display_name: "엔지니어링 팀",
      public_description: null,
    };
    mockPublications = [
      {
        published_slug: "cache-strategy",
        published_title: "캐시 계층 전략",
        published_content: `## 요구사항
- **관측 가능성**: 각 단계의 현재 상태를 확인 가능
- 재시도 안전성

## 관련 문서
- [[시스템-아키텍처]]
`,
        published_citations: [
          {
            anchor: "src:s1",
            source_title: "spec",
            snippet:
              "# background-job-lifecycle Specification ## Purpose 장시간 수집이 **at-least-once** 로 끝나야 한다.",
          },
        ],
        published_at: "2026-08-17T00:00:00Z",
      },
    ];

    const element = await PublicWikiPage({
      params: Promise.resolve({ slug: "engineering", page: "cache-strategy" }),
    });
    const { container } = render(element);

    expect(screen.getByText("관측 가능성")).toHaveClass("font-bold");
    expect(container.querySelectorAll("li").length).toBeGreaterThan(0);
    expect(container.textContent).not.toContain("시스템-아키텍처");
    expect(container.textContent).not.toContain("**");
    expect(screen.getByText(/at-least-once/)).toBeInTheDocument();
    expect(screen.queryByText(/Specification ## Purpose/)).toBeNull();
  });

  it("Ask 입력과 이모지 없이 3단 셸·신뢰 카드·가입 전환을 보여 준다", async () => {
    mockSettings = {
      workspace_id: "ws-1",
      workspace_slug: "engineering",
      allow_public_sharing: true,
      public_display_name: "엔지니어링 팀",
      public_description: null,
    };
    mockPublications = [
      {
        published_slug: "cache-strategy",
        published_title: "캐시 계층 전략",
        published_content: "본문",
        published_citations: [],
        published_at: "2026-08-17T00:00:00Z",
      },
    ];

    const element = await PublicWikiPage({
      params: Promise.resolve({ slug: "engineering", page: "cache-strategy" }),
    });
    const { container } = render(element);

    expect(container.querySelector(".public-header-grid")).not.toBeNull();
    expect(container.querySelector(".public-layout")).not.toBeNull();
    expect(screen.getByText("검증 및 승인됨")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "링크 복사" }),
    ).toBeInTheDocument();
    expect(
      screen.getAllByRole("link", { name: "시작하기" })[0],
    ).toHaveAttribute("href", "/signup");
    expect(
      screen.getByRole("link", { name: "NexusWiki 시작하기" }),
    ).toHaveAttribute("href", "/signup");
    expect(container.querySelector("textarea")).toBeNull();
    expect(container.querySelector("input")).toBeNull();
    expect(container.textContent).not.toMatch(/[\u{1F300}-\u{1FAFF}]/u);
  });

  it("같은 워크스페이스의 다른 발행본을 /p/ 링크로만 연결한다", async () => {
    mockSettings = {
      workspace_id: "ws-1",
      workspace_slug: "engineering",
      allow_public_sharing: true,
      public_display_name: "엔지니어링 팀",
      public_description: null,
    };
    mockPublications = [
      {
        published_slug: "cache-strategy",
        published_title: "캐시 계층 전략",
        published_content: "캐시 본문입니다.",
        published_citations: [],
        published_at: "2026-08-17T00:00:00Z",
      },
      {
        published_slug: "tenant-isolation",
        published_title: "테넌트 격리 아키텍처",
        published_content: "RLS 가 테넌트 경계를 강제합니다.",
        published_citations: [],
        published_at: "2026-08-17T00:00:00Z",
      },
    ];

    const element = await PublicWikiPage({
      params: Promise.resolve({ slug: "engineering", page: "cache-strategy" }),
    });
    const { container } = render(element);

    const siblingLinks = screen.getAllByRole("link", {
      name: /테넌트 격리 아키텍처/,
    });
    expect(siblingLinks.length).toBeGreaterThan(0);
    for (const link of siblingLinks) {
      expect(link).toHaveAttribute("href", "/p/engineering/tenant-isolation");
    }
    expect(container.querySelectorAll('a[href^="/w/"]')).toHaveLength(0);
    expect(screen.getByLabelText("공개 문서")).toHaveTextContent("2");
  });
});

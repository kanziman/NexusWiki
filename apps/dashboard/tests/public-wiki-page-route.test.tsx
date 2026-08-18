import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

const notFoundMock = vi.fn();
vi.mock("next/navigation", () => ({
  notFound: () => {
    notFoundMock();
    throw new Error("NEXT_NOT_FOUND");
  },
}));

let mockSettings: {
  workspace_id: string;
  workspace_slug: string;
  allow_public_sharing: boolean;
  public_display_name: string | null;
  public_description: string | null;
} | null = null;

let mockPub: {
  published_slug: string;
  published_title: string;
  published_content: string;
  published_citations: {
    anchor: string;
    source_title: string;
    snippet: string;
  }[];
  published_at: string;
} | null = null;

vi.mock("@/lib/supabase/server", () => ({
  createClient: vi.fn(async () => ({
    from: (table: string) => ({
      select: () => ({
        eq: () => ({
          eq: () => ({
            maybeSingle: async () => ({
              data:
                table === "workspace_public_settings" ? mockSettings : mockPub,
              error: null,
            }),
          }),
          maybeSingle: async () => ({
            data:
              table === "workspace_public_settings" ? mockSettings : mockPub,
            error: null,
          }),
        }),
      }),
    }),
  })),
}));

import PublicWikiPage from "@/app/p/[slug]/[page]/page";

describe("PublicWikiPage route", () => {
  it("calls notFound when public sharing is not enabled or workspace is not found", async () => {
    mockSettings = null;
    mockPub = null;

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

    mockPub = {
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
    };

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

    mockPub = {
      published_slug: "cache-strategy",
      published_title: "캐시 계층 전략",
      // 발행본은 내부 본문의 스냅샷이라 [[...]] 표기가 그대로 들어 있다.
      published_content:
        "# 개요\n자세한 내용은 [[테넌트 격리 스파인]]을 보세요.",
      published_citations: [],
      published_at: "2026-08-17T00:00:00Z",
    };

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
});

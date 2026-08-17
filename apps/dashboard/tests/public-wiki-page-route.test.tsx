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
});

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { KnowledgeGrid } from "@/components/KnowledgeGrid";

describe("KnowledgeGrid", () => {
  const samplePages = [
    {
      id: "page-1",
      title: "테넌트 격리 아키텍처",
      slug: "tenant-isolation",
      category: "concepts",
      verification_status: "verified",
      citation_count: 3,
    },
    {
      id: "page-2",
      title: "마이그레이션 가이드",
      slug: "migration-guide",
      category: "guides",
      verification_status: "unverified",
      citation_count: 1,
    },
  ];

  const sampleBacklog = [
    {
      target_slug: "cache-layer-strategy",
      reference_count: 4,
    },
  ];

  it("renders wiki documents and backlog items with metadata and badges", () => {
    render(
      <KnowledgeGrid
        workspaceId="ws-1"
        wikiPages={samplePages}
        backlogItems={sampleBacklog}
      />,
    );

    expect(screen.getByText("테넌트 격리 아키텍처")).toBeInTheDocument();
    expect(screen.getByText("검증됨")).toBeInTheDocument();
    expect(screen.getByText(/인용 원문 3개/)).toBeInTheDocument();

    expect(screen.getByText("cache-layer-strategy")).toBeInTheDocument();
    expect(screen.getByText(/위키 4곳에서 인용됨/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /소스 연결/ })).toHaveAttribute(
      "href",
      "/w/ws-1/sources",
    );
  });

  it("filters wiki documents when activeCategory is set", () => {
    render(
      <KnowledgeGrid
        workspaceId="ws-1"
        wikiPages={samplePages}
        backlogItems={sampleBacklog}
        activeCategory="concepts"
      />,
    );

    expect(screen.getByText("테넌트 격리 아키텍처")).toBeInTheDocument();
    expect(screen.queryByText("마이그레이션 가이드")).not.toBeInTheDocument();
  });

  it("shows empty states when wiki pages or backlog items are empty", () => {
    render(
      <KnowledgeGrid workspaceId="ws-1" wikiPages={[]} backlogItems={[]} />,
    );

    expect(
      screen.getByText("컴파일된 위키 문서가 아직 없습니다."),
    ).toBeInTheDocument();
    expect(
      screen.getByText("작성 대기 중인 백로그가 없습니다."),
    ).toBeInTheDocument();
  });
});

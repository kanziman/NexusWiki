import { render, screen, within } from "@testing-library/react";
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
    expect(screen.getByText("개념")).toBeInTheDocument();
    expect(screen.getByText(/인용 원문 3개/)).toBeInTheDocument();

    expect(screen.getByText("cache-layer-strategy")).toBeInTheDocument();
    expect(screen.getByText(/위키 4곳에서 인용됨/)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /cache-layer-strategy/ }),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "소스 추가" })).toHaveAttribute(
      "href",
      "/w/ws-1/sources?prefillTitle=cache-layer-strategy&tab=text",
    );
    expect(screen.getByRole("link", { name: "소스 연결" })).toHaveAttribute(
      "href",
      "/w/ws-1/sources",
    );
  });

  it("opens backlog detail modal when a backlog item is clicked", async () => {
    const user = (await import("@testing-library/user-event")).default.setup();
    render(
      <KnowledgeGrid
        workspaceId="ws-1"
        wikiPages={samplePages}
        backlogItems={[
          {
            target_slug: "cache-layer-strategy",
            display_title: "캐시 계층 전략",
            reference_count: 4,
            impact: 4,
            first_detected_at: "2026-08-20T00:00:00Z",
            referencing_pages: [
              {
                id: "page-1",
                slug: "tenant-isolation",
                title: "테넌트 격리 아키텍처",
                excerpt: "캐시 계층 전략을 적용한다.",
              },
            ],
          },
        ]}
      />,
    );

    const button = screen.getByRole("button", { name: /캐시 계층 전략/ });
    await user.click(button);

    // Dialog Title
    expect(
      screen.getByText(
        (_, el) => el?.textContent === "캐시 계층 전략을 적용한다.",
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByText("캐시 계층 전략", { selector: "mark" }),
    ).toBeInTheDocument();
    expect(
      within(screen.getByRole("dialog")).getByRole("link", {
        name: "소스 추가",
      }),
    ).toHaveAttribute(
      "href",
      "/w/ws-1/sources?prefillTitle=%EC%BA%90%EC%8B%9C%20%EA%B3%84%EC%B8%B5%20%EC%A0%84%EB%9E%B5&tab=text",
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

  it("홈 대시보드 피드에서 위키 문서는 최대 5개, 백로그 항목은 최대 4개로 노출을 제한한다", () => {
    const manyPages = Array.from({ length: 15 }, (_, i) => ({
      id: `page-${i + 1}`,
      title: `위키 문서 ${i + 1}`,
      slug: `wiki-page-${i + 1}`,
      category: "concepts",
      verification_status: "verified",
      citation_count: 1,
    }));

    const manyBacklogs = Array.from({ length: 12 }, (_, i) => ({
      target_slug: `backlog-topic-${i + 1}`,
      display_title: `백로그 주제 ${i + 1}`,
      reference_count: 2,
    }));

    render(
      <KnowledgeGrid
        workspaceId="ws-1"
        wikiPages={manyPages}
        backlogItems={manyBacklogs}
      />,
    );

    // 헤더에는 전체 개수 배지(15, 12)가 유지된다
    expect(screen.getByText("15")).toBeInTheDocument();
    expect(screen.getByText("12")).toBeInTheDocument();

    // 위키 문서는 1~5까지만 렌더링되고 6~15는 렌더링되지 않는다
    expect(screen.getByText("위키 문서 1")).toBeInTheDocument();
    expect(screen.getByText("위키 문서 5")).toBeInTheDocument();
    expect(screen.queryByText("위키 문서 6")).not.toBeInTheDocument();

    // 백로그는 1~4까지만 렌더링되고 5~12는 렌더링되지 않는다
    expect(screen.getByText("백로그 주제 1")).toBeInTheDocument();
    expect(screen.getByText("백로그 주제 4")).toBeInTheDocument();
    expect(screen.queryByText("백로그 주제 5")).not.toBeInTheDocument();

    // 상한을 넘긴 항목은 각 열의 전용 화면에서 계속 도달할 수 있어야 한다.
    // 이 단언이 없으면 링크를 지워도 테스트가 통과해, 잘린 항목이 조용히
    // 도달 불가능해진다.
    expect(
      document.querySelector('[data-od-id="view-all-documents"]'),
    ).toHaveAttribute("href", "/w/ws-1/wiki");
    expect(
      document.querySelector('[data-od-id="view-all-backlog"]'),
    ).toHaveAttribute("href", "/w/ws-1/backlog");

    // 두 열의 탈출구 링크는 같은 역할이므로 같은 라벨을 쓴다. href 만 단언하면
    // 라벨이 조용히 갈라져도 통과한다 — 상한을 낮춘 화면에서 이 링크는 잘린
    // 항목에 도달하는 유일한 경로다.
    expect(
      document.querySelector('[data-od-id="view-all-documents"]'),
    ).toHaveTextContent("전체 보기");
    expect(
      document.querySelector('[data-od-id="view-all-backlog"]'),
    ).toHaveTextContent("전체 보기");

    // 홈 요약 섹션도 목적지의 정본 명칭으로 시작해야 한다. 괄호 보조 설명은
    // 허용되지만 정본 명칭을 대체할 수는 없다.
    const backlogSection = document.querySelector(
      '[data-od-id="writing-backlog-section"]',
    );
    expect(backlogSection).toHaveTextContent("지식 공백");
    expect(backlogSection).not.toHaveTextContent("미완성 백로그");
  });
});

import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { BacklogItem, BacklogList } from "@/components/BacklogList";

describe("BacklogList", () => {
  it("renders empty state when there are no backlog items", () => {
    render(<BacklogList workspaceId="ws-1" initialItems={[]} />);

    expect(
      screen.getByText("작성 대기 중인 백로그가 없습니다"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("모든 위키 링크가 정상적으로 연결되어 있습니다."),
    ).toBeInTheDocument();
  });

  it("renders backlog items, top stats, and prefilled source creation links", () => {
    const items: BacklogItem[] = [
      {
        target_slug: "캐시-계층-전략",
        impact: 3,
        first_detected_at: "2026-08-15T00:00:00Z",
        referencing_pages: [
          { id: "page-1", slug: "arch-guide", title: "아키텍처 가이드" },
          { id: "page-2", slug: "perf-tuning", title: "성능 튜닝" },
        ],
      },
      {
        target_slug: "인증-흐름",
        impact: 1,
        first_detected_at: "2026-08-16T00:00:00Z",
        referencing_pages: [
          { id: "page-3", slug: "auth-spec", title: "인증 명세" },
        ],
      },
    ];

    render(<BacklogList workspaceId="ws-1" initialItems={items} />);

    // 상단 통계
    expect(screen.getByText("2")).toBeInTheDocument(); // 2개 주제
    expect(screen.getByText("3")).toBeInTheDocument(); // 3개 문서

    // 항목 렌더링
    expect(screen.getByText("캐시 계층 전략")).toBeInTheDocument();
    expect(screen.getByText("참조 3회")).toBeInTheDocument();
    expect(screen.getByText("인증 흐름")).toBeInTheDocument();
    expect(screen.getByText("참조 1회")).toBeInTheDocument();

    // 인용 문서 링크
    expect(screen.getByText("아키텍처 가이드")).toBeInTheDocument();
    expect(screen.getByText("성능 튜닝")).toBeInTheDocument();

    // 소스 추가 링크
    const addSourceLinks = screen.getAllByRole("link", { name: /소스 추가/ });
    expect(addSourceLinks).toHaveLength(2);
    expect(addSourceLinks[0]).toHaveAttribute(
      "href",
      "/w/ws-1/sources?prefillTitle=%EC%BA%90%EC%8B%9C%20%EA%B3%84%EC%B8%B5%20%EC%A0%84%EB%9E%B5&tab=text",
    );
  });

  it("filters backlog items based on search input", () => {
    const items: BacklogItem[] = [
      {
        target_slug: "캐시-계층-전략",
        impact: 3,
        first_detected_at: "2026-08-15T00:00:00Z",
        referencing_pages: [
          { id: "page-1", slug: "arch-guide", title: "아키텍처 가이드" },
        ],
      },
      {
        target_slug: "인증-흐름",
        impact: 1,
        first_detected_at: "2026-08-16T00:00:00Z",
        referencing_pages: [
          { id: "page-3", slug: "auth-spec", title: "인증 명세" },
        ],
      },
    ];

    render(<BacklogList workspaceId="ws-1" initialItems={items} />);

    const searchInput = screen.getByRole("textbox", { name: "백로그 검색" });

    fireEvent.change(searchInput, { target: { value: "캐시" } });
    expect(screen.getByText("캐시 계층 전략")).toBeInTheDocument();
    expect(screen.queryByText("인증 흐름")).not.toBeInTheDocument();

    fireEvent.change(searchInput, { target: { value: "존재하지않음" } });
    expect(screen.getByText("검색 결과가 없습니다")).toBeInTheDocument();
  });
});

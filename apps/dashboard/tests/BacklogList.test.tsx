import { fireEvent, render, screen, within } from "@testing-library/react";
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
        display_title: "캐시 계층 전략",
        impact: 3,
        first_detected_at: "2026-08-15T00:00:00Z",
        referencing_pages: [
          { id: "page-1", slug: "arch-guide", title: "아키텍처 가이드" },
          { id: "page-2", slug: "perf-tuning", title: "성능 튜닝" },
        ],
      },
      {
        target_slug: "인증-흐름",
        display_title: "인증 흐름",
        impact: 1,
        first_detected_at: "2026-08-16T00:00:00Z",
        referencing_pages: [
          { id: "page-3", slug: "auth-spec", title: "인증 명세" },
        ],
      },
    ];

    render(<BacklogList workspaceId="ws-1" initialItems={items} />);

    // 상단 통계. ⚠️ 화면 전체에서 "3"을 찾으면 안 된다 — 인용 빈도 열이 같은
    // 숫자를 렌더하므로 요약 영역 안으로 좁힌다.
    const summary = within(screen.getByRole("region", { name: "백로그 요약" }));
    expect(summary.getByText("2")).toBeInTheDocument(); // 2개 주제
    expect(summary.getByText("3")).toBeInTheDocument(); // 3개 문서

    // 항목 렌더링. 인용 빈도는 배지가 아니라 표의 정렬 축 열이다(PRD §3.2).
    const table = within(screen.getByRole("table"));
    expect(screen.getByText("캐시 계층 전략")).toBeInTheDocument();
    expect(table.getByText("3")).toBeInTheDocument();
    expect(screen.getByText("인증 흐름")).toBeInTheDocument();
    expect(table.getByText("1")).toBeInTheDocument();

    // 인용 빈도 내림차순 — 첫 행이 impact 3 이어야 한다(PRD §3.2 정렬 기본값).
    const rows = screen.getAllByRole("row").slice(1); // 헤더 행 제외
    expect(within(rows[0]).getByText("캐시 계층 전략")).toBeInTheDocument();

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
        display_title: "캐시 계층 전략",
        impact: 3,
        first_detected_at: "2026-08-15T00:00:00Z",
        referencing_pages: [
          { id: "page-1", slug: "arch-guide", title: "아키텍처 가이드" },
        ],
      },
      {
        target_slug: "인증-흐름",
        display_title: "인증 흐름",
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

  it("행 라벨은 서버가 복원한 원문 표기를 쓰고, 원본 slug는 보조 줄에 병기한다", () => {
    // add-backlog-topic-context: display_title은 인용 문서 본문의 [[표기]]에서
    // 복원한 값이라 target_slug의 하이픈 역변환과 다를 수 있다(대소문자·문장부호
    // 보존). 이 컴포넌트는 표기를 계산하지 않고 서버가 만든 값을 그대로 쓴다.
    const items: BacklogItem[] = [
      {
        target_slug: "rls-정책v2",
        display_title: "RLS 정책(v2)",
        impact: 1,
        first_detected_at: "2026-08-15T00:00:00Z",
        referencing_pages: [
          { id: "page-1", slug: "arch-guide", title: "아키텍처 가이드" },
        ],
      },
    ];

    render(<BacklogList workspaceId="ws-1" initialItems={items} />);

    expect(screen.getByText("RLS 정책(v2)")).toBeInTheDocument();
    expect(screen.getByText("rls-정책v2")).toBeInTheDocument();

    // 소스 추가 동선도 slug가 아니라 표기를 prefill한다.
    const addSourceLink = screen.getByRole("link", { name: /소스 추가/ });
    expect(addSourceLink).toHaveAttribute(
      "href",
      `/w/ws-1/sources?prefillTitle=${encodeURIComponent("RLS 정책(v2)")}&tab=text`,
    );
  });

  it("표기를 복원하지 못한 주제는 slug 역변환으로 폴백한 display_title을 그대로 렌더한다", () => {
    // 폴백 계산은 page.tsx(서버)가 하고, 이 컴포넌트는 결과 문자열만 소비한다 —
    // 여기서는 그 계약을 재확인만 한다.
    const items: BacklogItem[] = [
      {
        target_slug: "아직-못-찾은-주제",
        display_title: "아직 못 찾은 주제",
        impact: 1,
        first_detected_at: "2026-08-15T00:00:00Z",
        referencing_pages: [],
      },
    ];

    render(<BacklogList workspaceId="ws-1" initialItems={items} />);

    expect(screen.getByText("아직 못 찾은 주제")).toBeInTheDocument();
    expect(screen.getByText("아직-못-찾은-주제")).toBeInTheDocument();
  });

  describe("상세 패널 (add-backlog-topic-context 2.1)", () => {
    const items: BacklogItem[] = [
      {
        target_slug: "캐시-계층-전략",
        display_title: "캐시 계층 전략",
        impact: 3,
        first_detected_at: "2026-08-15T00:00:00Z",
        referencing_pages: [
          { id: "page-1", slug: "arch-guide", title: "아키텍처 가이드" },
          { id: "page-2", slug: "perf-tuning", title: "성능 튜닝" },
        ],
      },
    ];

    it("주제 행을 열면 패널이 표기·최초 감지 시각·인용 위키·소스 추가 동선을 보여준다", () => {
      render(<BacklogList workspaceId="ws-1" initialItems={items} />);

      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();

      fireEvent.click(screen.getByRole("button", { name: /캐시 계층 전략/ }));

      const panel = within(screen.getByRole("dialog"));
      expect(
        panel.getByRole("heading", { name: "캐시 계층 전략" }),
      ).toBeInTheDocument();
      expect(panel.getByText("캐시-계층-전략")).toBeInTheDocument();
      expect(panel.getByText(/최초 감지/)).toBeInTheDocument();

      // 인용 중인 위키 목록 — 목록 행의 doc-chips와 별개로 패널 안에 또 있다.
      expect(
        panel.getByRole("link", { name: "아키텍처 가이드" }),
      ).toHaveAttribute("href", "/w/ws-1/wiki/arch-guide");
      expect(panel.getByRole("link", { name: "성능 튜닝" })).toHaveAttribute(
        "href",
        "/w/ws-1/wiki/perf-tuning",
      );

      // 소스 추가는 목록 행과 같은 목적지다.
      expect(panel.getByRole("link", { name: "소스 추가" })).toHaveAttribute(
        "href",
        `/w/ws-1/sources?prefillTitle=${encodeURIComponent("캐시 계층 전략")}&tab=text`,
      );
    });

    it("닫기 버튼을 누르면 패널이 사라진다", () => {
      render(<BacklogList workspaceId="ws-1" initialItems={items} />);

      fireEvent.click(screen.getByRole("button", { name: /캐시 계층 전략/ }));
      expect(screen.getByRole("dialog")).toBeInTheDocument();

      fireEvent.click(screen.getByRole("button", { name: "닫기" }));
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });

    it("인용 문서가 없는 주제는 패널에 안내 문구를 보여준다", () => {
      const emptyRefsItems: BacklogItem[] = [
        {
          target_slug: "고아-주제",
          display_title: "고아 주제",
          impact: 1,
          first_detected_at: "2026-08-15T00:00:00Z",
          referencing_pages: [],
        },
      ];

      render(<BacklogList workspaceId="ws-1" initialItems={emptyRefsItems} />);
      fireEvent.click(screen.getByRole("button", { name: /고아 주제/ }));

      const panel = within(screen.getByRole("dialog"));
      expect(panel.getByText("인용 문서 없음")).toBeInTheDocument();
    });
  });
});

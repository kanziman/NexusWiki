import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { BacklogItem, BacklogList } from "@/components/BacklogList";

describe("BacklogList", () => {
  it("화면 제목은 정본 명칭 지식 공백을 쓴다", () => {
    render(<BacklogList workspaceId="ws-1" initialItems={[]} />);

    // 목적지 이름이 표면마다 갈리지 않아야 한다. 이 단언이 없으면 heading 만
    // 옛 명칭으로 되돌아가도 전체 테스트가 통과한다.
    expect(
      screen.getByRole("heading", { level: 1, name: "지식 공백" }),
    ).toBeInTheDocument();
  });

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
          {
            id: "page-1",
            slug: "arch-guide",
            title: "아키텍처 가이드",
            excerpt: null,
          },
          {
            id: "page-2",
            slug: "perf-tuning",
            title: "성능 튜닝",
            excerpt: null,
          },
        ],
      },
      {
        target_slug: "인증-흐름",
        display_title: "인증 흐름",
        impact: 1,
        first_detected_at: "2026-08-16T00:00:00Z",
        referencing_pages: [
          {
            id: "page-3",
            slug: "auth-spec",
            title: "인증 명세",
            excerpt: null,
          },
        ],
      },
    ];

    render(<BacklogList workspaceId="ws-1" initialItems={items} />);

    // 상단 통계. ⚠️ 화면 전체에서 "3"을 찾으면 안 된다 — 인용 빈도 열과
    // 최다 인용 카드가 같은 숫자를 렌더할 수 있으므로 각 지표 카드로 좁힌다.
    expect(
      within(screen.getByTestId("backlog-metric-unresolved")).getByText("2"),
    ).toBeInTheDocument(); // 2개 주제
    expect(
      within(screen.getByTestId("backlog-metric-affected-wikis")).getByText(
        "3",
      ),
    ).toBeInTheDocument(); // 3개 문서

    // 항목 렌더링. 인용 빈도는 배지가 아니라 표의 정렬 축 열이다(PRD §3.2).
    // ⚠️ 주제명은 최다 인용/최장 대기 벤토 카드에도 나타날 수 있으므로 표
    // 안으로 좁힌다.
    const table = within(screen.getByRole("table"));
    expect(table.getByText("캐시 계층 전략")).toBeInTheDocument();
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
          {
            id: "page-1",
            slug: "arch-guide",
            title: "아키텍처 가이드",
            excerpt: null,
          },
        ],
      },
      {
        target_slug: "인증-흐름",
        display_title: "인증 흐름",
        impact: 1,
        first_detected_at: "2026-08-16T00:00:00Z",
        referencing_pages: [
          {
            id: "page-3",
            slug: "auth-spec",
            title: "인증 명세",
            excerpt: null,
          },
        ],
      },
    ];

    render(<BacklogList workspaceId="ws-1" initialItems={items} />);

    const searchInput = screen.getByRole("textbox", { name: "지식 공백 검색" });

    fireEvent.change(searchInput, { target: { value: "캐시" } });
    // ⚠️ 벤토 요약은 검색어와 무관하게 전체 데이터를 반영하므로, 최다
    // 인용/최장 대기 카드가 같은 주제명을 계속 보여줄 수 있다. 표 안으로
    // 좁혀 필터링된 행만 확인한다.
    const table = within(screen.getByRole("table"));
    expect(table.getByText("캐시 계층 전략")).toBeInTheDocument();
    expect(table.queryByText("인증 흐름")).not.toBeInTheDocument();

    fireEvent.change(searchInput, { target: { value: "존재하지않음" } });
    expect(screen.getByText("검색 결과가 없습니다")).toBeInTheDocument();
  });

  describe("우선순위 요약 벤토", () => {
    const bentoItems: BacklogItem[] = [
      {
        target_slug: "캐시-계층-전략",
        display_title: "캐시 계층 전략",
        impact: 3,
        first_detected_at: "2026-08-16T00:00:00Z",
        referencing_pages: [
          {
            id: "page-1",
            slug: "arch-guide",
            title: "아키텍처 가이드",
            excerpt: null,
          },
          {
            id: "page-2",
            slug: "perf-tuning",
            title: "성능 튜닝",
            excerpt: null,
          },
        ],
      },
      {
        target_slug: "인증-흐름",
        display_title: "인증 흐름",
        impact: 1,
        first_detected_at: "2026-08-15T00:00:00Z",
        referencing_pages: [
          {
            id: "page-3",
            slug: "auth-spec",
            title: "인증 명세",
            excerpt: null,
          },
        ],
      },
    ];

    it("네 지표가 목록과 일치한다 — 최다 인용과 최장 대기가 서로 다른 주제를 가리킨다", () => {
      render(<BacklogList workspaceId="ws-1" initialItems={bentoItems} />);

      expect(
        within(screen.getByTestId("backlog-metric-unresolved")).getByText("2"),
      ).toBeInTheDocument();
      expect(
        within(screen.getByTestId("backlog-metric-affected-wikis")).getByText(
          "3",
        ),
      ).toBeInTheDocument();
      // 최다 인용 — impact 3인 "캐시 계층 전략"
      expect(
        within(screen.getByTestId("backlog-metric-most-cited")).getByText(
          "캐시 계층 전략",
        ),
      ).toBeInTheDocument();
      // 최장 대기 — first_detected_at 이 더 이른 "인증 흐름"
      expect(
        within(screen.getByTestId("backlog-metric-longest-waiting")).getByText(
          "인증 흐름",
        ),
      ).toBeInTheDocument();
    });

    it("최다 인용이 동률이면 target_slug 오름차순으로 결정적으로 고른다", () => {
      const tiedItems: BacklogItem[] = [
        {
          target_slug: "나중-주제",
          display_title: "나중 주제",
          impact: 2,
          first_detected_at: "2026-08-15T00:00:00Z",
          referencing_pages: [],
        },
        {
          target_slug: "가장-먼저-주제",
          display_title: "가장 먼저 주제",
          impact: 2,
          first_detected_at: "2026-08-15T00:00:00Z",
          referencing_pages: [],
        },
      ];

      render(<BacklogList workspaceId="ws-1" initialItems={tiedItems} />);

      expect(
        within(screen.getByTestId("backlog-metric-most-cited")).getByText(
          "가장 먼저 주제",
        ),
      ).toBeInTheDocument();
    });

    it("주제가 없으면 벤토를 렌더하지 않는다", () => {
      render(<BacklogList workspaceId="ws-1" initialItems={[]} />);

      expect(screen.queryByLabelText("지식 공백 요약")).not.toBeInTheDocument();
    });
  });

  describe("인용 빈도 필터", () => {
    const filterItems: BacklogItem[] = [
      {
        target_slug: "다중-인용-a",
        display_title: "다중 인용 주제 A",
        impact: 2,
        first_detected_at: "2026-08-15T00:00:00Z",
        referencing_pages: [],
      },
      {
        target_slug: "다중-인용-b",
        display_title: "다중 인용 주제 B",
        impact: 3,
        first_detected_at: "2026-08-15T00:00:00Z",
        referencing_pages: [],
      },
      {
        target_slug: "단일-인용",
        display_title: "단일 인용 주제",
        impact: 1,
        first_detected_at: "2026-08-15T00:00:00Z",
        referencing_pages: [],
      },
    ];

    it("다중 인용 필터를 고르면 impact 2 이상인 주제만 남는다", () => {
      render(<BacklogList workspaceId="ws-1" initialItems={filterItems} />);

      const multiTab = screen.getByRole("tab", { name: "다중 인용 2" });
      fireEvent.click(multiTab);

      const table = within(screen.getByRole("table"));
      expect(table.getByText("다중 인용 주제 A")).toBeInTheDocument();
      expect(table.getByText("다중 인용 주제 B")).toBeInTheDocument();
      expect(table.queryByText("단일 인용 주제")).not.toBeInTheDocument();
    });

    it("단일 인용 필터를 고르면 impact 1인 주제만 남는다", () => {
      render(<BacklogList workspaceId="ws-1" initialItems={filterItems} />);

      const singleTab = screen.getByRole("tab", { name: "단일 인용 1" });
      fireEvent.click(singleTab);

      const table = within(screen.getByRole("table"));
      expect(table.getByText("단일 인용 주제")).toBeInTheDocument();
      expect(table.queryByText("다중 인용 주제 A")).not.toBeInTheDocument();
      expect(table.queryByText("다중 인용 주제 B")).not.toBeInTheDocument();
    });

    it("필터와 검색어가 함께 걸린다 — 한쪽이 다른 쪽을 리셋하지 않는다", () => {
      render(<BacklogList workspaceId="ws-1" initialItems={filterItems} />);

      fireEvent.click(screen.getByRole("tab", { name: "다중 인용 2" }));
      fireEvent.change(
        screen.getByRole("textbox", { name: "지식 공백 검색" }),
        { target: { value: "B" } },
      );

      const table = within(screen.getByRole("table"));
      expect(table.getByText("다중 인용 주제 B")).toBeInTheDocument();
      expect(table.queryByText("다중 인용 주제 A")).not.toBeInTheDocument();
      expect(table.queryByText("단일 인용 주제")).not.toBeInTheDocument();
    });
  });

  it("인용 위키가 많아도 칩 2개와 잔여 개수만 렌더한다", () => {
    const items: BacklogItem[] = [
      {
        target_slug: "다중-인용-공백",
        display_title: "다중 인용 공백",
        impact: 4,
        first_detected_at: "2026-08-15T00:00:00Z",
        referencing_pages: [
          { id: "p1", slug: "one", title: "위키 하나", excerpt: null },
          { id: "p2", slug: "two", title: "위키 둘", excerpt: null },
          { id: "p3", slug: "three", title: "위키 셋", excerpt: null },
          { id: "p4", slug: "four", title: "위키 넷", excerpt: null },
        ],
      },
    ];

    render(<BacklogList workspaceId="ws-1" initialItems={items} />);

    const table = within(screen.getByRole("table"));
    expect(table.getByText("위키 하나")).toBeInTheDocument();
    expect(table.getByText("위키 둘")).toBeInTheDocument();
    expect(table.queryByText("위키 셋")).not.toBeInTheDocument();
    expect(table.getByText("+2개 더")).toBeInTheDocument();
  });

  it("조회가 실패하면 빈 상태 문구 대신 불러오지 못했음을 알린다", () => {
    render(<BacklogList workspaceId="ws-1" initialItems={[]} loadFailed />);

    expect(
      screen.getByText("지식 공백을 불러오지 못했습니다"),
    ).toBeInTheDocument();
    expect(
      screen.queryByText("작성 대기 중인 백로그가 없습니다"),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByText("모든 위키 링크가 정상적으로 연결되어 있습니다."),
    ).not.toBeInTheDocument();
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
          {
            id: "page-1",
            slug: "arch-guide",
            title: "아키텍처 가이드",
            excerpt: null,
          },
        ],
      },
    ];

    render(<BacklogList workspaceId="ws-1" initialItems={items} />);

    // ⚠️ 단일 항목이면 최다 인용·최장 대기 카드가 모두 같은 주제를 가리켜
    // 표기가 벤토와 표 양쪽에 나타난다. 표 안으로 좁힌다.
    expect(
      within(screen.getByRole("table")).getByText("RLS 정책(v2)"),
    ).toBeInTheDocument();
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

    // ⚠️ 단일 항목이면 최다 인용·최장 대기 카드가 모두 같은 주제를 가리켜
    // 표기가 벤토와 표 양쪽에 나타난다. 표 안으로 좁힌다.
    expect(
      within(screen.getByRole("table")).getByText("아직 못 찾은 주제"),
    ).toBeInTheDocument();
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
          {
            id: "page-1",
            slug: "arch-guide",
            title: "아키텍처 가이드",
            excerpt: null,
          },
          {
            id: "page-2",
            slug: "perf-tuning",
            title: "성능 튜닝",
            excerpt: null,
          },
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

  describe("인용 문맥 발췌 (add-backlog-topic-context 3.1)", () => {
    it("인용 문서마다 서버가 만든 발췌를 하나씩 보여준다", () => {
      const items: BacklogItem[] = [
        {
          target_slug: "캐시-계층-전략",
          display_title: "캐시 계층 전략",
          impact: 2,
          first_detected_at: "2026-08-15T00:00:00Z",
          referencing_pages: [
            {
              id: "page-1",
              slug: "arch-guide",
              title: "아키텍처 가이드",
              excerpt: "…읽기 경로는 [캐시 계층 전략]을 따라 조회한다…",
            },
            {
              id: "page-2",
              slug: "perf-tuning",
              title: "성능 튜닝",
              excerpt: null,
            },
          ],
        },
      ];

      render(<BacklogList workspaceId="ws-1" initialItems={items} />);
      fireEvent.click(screen.getByRole("button", { name: /캐시 계층 전략/ }));

      const panel = within(screen.getByRole("dialog"));
      expect(
        panel.getByText(
          (_, el) =>
            el?.textContent ===
            "…읽기 경로는 [캐시 계층 전략]을 따라 조회한다…",
        ),
      ).toBeInTheDocument();
      expect(
        panel.getByText("캐시 계층 전략", { selector: "mark" }),
      ).toBeInTheDocument();

      // 발췌가 없는 문서(excerpt: null)는 링크만 있고 발췌 문단이 없다 —
      // 문단을 빈 채로 그리지 않는다.
      const secondPageLink = panel.getByRole("link", { name: "성능 튜닝" });
      expect(secondPageLink.nextElementSibling).toBeNull();
    });

    it("발췌는 링크 접근성 이름에 섞이지 않는다 — 별도 문단으로 렌더한다", () => {
      // 발췌를 <Link> 안에 넣으면 스크린 리더가 링크 이름으로 발췌 전체를
      // 읽는다. 링크 이름은 문서 제목만이어야 한다.
      const items: BacklogItem[] = [
        {
          target_slug: "캐시-계층-전략",
          display_title: "캐시 계층 전략",
          impact: 1,
          first_detected_at: "2026-08-15T00:00:00Z",
          referencing_pages: [
            {
              id: "page-1",
              slug: "arch-guide",
              title: "아키텍처 가이드",
              excerpt: "…발췌 문장…",
            },
          ],
        },
      ];

      render(<BacklogList workspaceId="ws-1" initialItems={items} />);
      fireEvent.click(screen.getByRole("button", { name: /캐시 계층 전략/ }));

      const panel = within(screen.getByRole("dialog"));
      expect(
        panel.getByRole("link", { name: "아키텍처 가이드" }),
      ).toBeInTheDocument();
    });

    it("8개 초과의 백로그 항목이 있을 때 페이지당 8개씩 분할하여 페이지네이션한다", () => {
      const manyItems: BacklogItem[] = Array.from({ length: 14 }, (_, i) => ({
        target_slug: `backlog-item-${i + 1}`,
        display_title: `백로그 주제 ${i + 1}`,
        impact: 1,
        first_detected_at: "2026-08-15T00:00:00Z",
        referencing_pages: [],
      }));

      render(<BacklogList workspaceId="ws-1" initialItems={manyItems} />);

      // ⚠️ 벤토 요약(최다 인용·최장 대기 카드)은 페이지네이션과 무관하게
      // 전체 14개 항목 중 하나(동률 결정 규칙상 "백로그 주제 1")를 계속
      // 보여준다. 표 안으로 좁혀 현재 페이지에 실제로 렌더된 행만 확인한다.
      let table = within(screen.getByRole("table"));

      // 1페이지 항목(1~8) 확인
      expect(table.getByText("백로그 주제 1")).toBeInTheDocument();
      expect(table.getByText("백로그 주제 8")).toBeInTheDocument();
      expect(table.queryByText("백로그 주제 9")).not.toBeInTheDocument();

      // 2페이지로 이동
      const page2Btn = screen.getByRole("button", { name: "2 페이지" });
      fireEvent.click(page2Btn);

      table = within(screen.getByRole("table"));
      expect(table.queryByText("백로그 주제 1")).not.toBeInTheDocument();
      expect(table.getByText("백로그 주제 9")).toBeInTheDocument();
      expect(table.getByText("백로그 주제 14")).toBeInTheDocument();
    });
  });
});

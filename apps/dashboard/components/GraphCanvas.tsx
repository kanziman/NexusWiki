"use client";

import cytoscape from "cytoscape";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { createClient } from "@/lib/supabase/client";

export type GraphCanvasProps = {
  workspaceId: string;
  category: string | null;
};

type WikiNode = {
  id: string;
  slug: string;
  title: string;
  category: string;
};

type WikiEdge = {
  from_wiki_id: string;
  to_wiki_id: string;
};

// UI-06 카테고리별 노드 색상 — --color-primary는 UI-SPEC Color 섹션에서
// CTA/워크스페이스 스위처 활성 표시/인용 마커/잡 스테퍼 현재 단계 전용으로
// 예약돼 있으므로 여기서는 재사용하지 않는다. 팔레트의 나머지 비-primary
// 색(luxe/plus 서브브랜드 2개 + 중립 톤 2개)을 그대로 쓴다 — Task 3 <action>
// "e.g. --color-luxe/--color-plus plus two neutral tones" 그대로.
const CATEGORY_COLORS: Record<string, string> = {
  concepts: "#460479", // --color-luxe
  entities: "#92174d", // --color-plus
  guides: "#6a6a6a", // --color-muted
  maps: "#3f3f3f", // --color-body
};
const DEFAULT_NODE_COLOR = "#6a6a6a"; // --color-muted, 알 수 없는 category용 방어선

// UI-SPEC 카피 계약(Graph canvas(UI-06)) — 문구 한 글자도 바꾸지 않는다.
const CAP_NOTICE =
  "이 워크스페이스는 그래프 표시 한도(1,000개 노드)를 초과했습니다 — 카테고리 필터로 범위를 좁혀주세요.";
const EMPTY_HEADING = "표시할 노드가 없습니다";
const EMPTY_BODY =
  "카테고리 필터를 초기화하거나 다른 워크스페이스를 선택하세요.";
const LOAD_ERROR = "그래프를 불러오지 못했습니다. 새로고침해주세요.";

// PostgREST의 워크스페이스 전역 max_rows 캡(supabase/config.toml) 하나만
// 근거로 삼는다 — Task 1이 기록한, 단일 시드 이웃 탐색용 그래프 RPC(자체
// 200행 캡)를 쓰지 않는 결정의 직접 결과다 (근거: 이 PLAN.md Task 1).
const PAGE_ROW_CAP = 1000;

type LoadState =
  | { status: "loading" }
  | { status: "error" }
  | { status: "empty" }
  | { status: "ready"; nodes: WikiNode[]; edges: WikiEdge[]; capped: boolean };

// GraphCanvas.tsx는 (page.tsx가 아니라) 이 컴포넌트 자체가 클라이언트에서
// 직접 fetch한다 — ?category= URL 변경마다 전체 페이지 네비게이션/RSC
// 재요청 없이 재조회하기 위해서다. Phase 6의 다른 표면은 전부 서버 사이드
// 1차 fetch를 쓰지만, 이 화면만 그 규칙에서 벗어난다(Task 3 <action> 마지막
// 문단 참조).
export function GraphCanvas({ workspaceId, category }: GraphCanvasProps) {
  const router = useRouter();
  const containerRef = useRef<HTMLDivElement>(null);
  const [state, setState] = useState<LoadState>({ status: "loading" });

  useEffect(() => {
    let cancelled = false;
    setState({ status: "loading" });

    async function load() {
      const supabase = createClient();

      let nodeQuery = supabase
        .from("wiki_pages")
        .select("id,slug,title,category", { count: "exact" })
        .eq("workspace_id", workspaceId);
      if (category) {
        nodeQuery = nodeQuery.eq("category", category);
      }

      const {
        data: nodes,
        count,
        error: nodeError,
      } = await nodeQuery.returns<WikiNode[]>();

      if (cancelled) return;
      if (nodeError || nodes === null) {
        setState({ status: "error" });
        return;
      }

      if (nodes.length === 0) {
        setState({ status: "empty" });
        return;
      }

      // count가 있으면 그것만으로 판단한다(1000행 페이지와 "정확히 1000개"를
      // 구분할 수 있다) — count 헤더가 어떤 이유로든 없을 때만 페이지 길이로
      // 폴백한다. 06-REVIEW.md WR-01: 이전에는 `||`로 두 조건을 합쳐서, count가
      // 정확히 1000일 때(캡 아님)도 nodes.length === PAGE_ROW_CAP이 참이 되어
      // 오탐(false positive) 캡 배너가 떴다.
      const capped =
        count !== null ? count > PAGE_ROW_CAP : nodes.length === PAGE_ROW_CAP;

      const nodeIds = nodes.map((node) => node.id);
      const { data: edges, error: edgeError } = await supabase
        .from("wiki_links")
        .select("from_wiki_id,to_wiki_id")
        .eq("workspace_id", workspaceId)
        .not("to_wiki_id", "is", null)
        .in("from_wiki_id", nodeIds)
        .returns<WikiEdge[]>();

      if (cancelled) return;
      if (edgeError || edges === null) {
        setState({ status: "error" });
        return;
      }

      setState({ status: "ready", nodes, edges, capped });
    }

    load().catch(() => {
      if (!cancelled) setState({ status: "error" });
    });

    return () => {
      cancelled = true;
    };
  }, [workspaceId, category]);

  useEffect(() => {
    if (state.status !== "ready" || !containerRef.current) return;

    // 조회된 노드 집합 밖을 가리키는 엣지는 그리지 않는다 — from/to 둘 다
    // nodeIds .in() 필터를 통과했더라도, to_wiki_id가 카테고리 필터로 배제된
    // 노드를 가리킬 수 있다(엣지 쿼리는 from_wiki_id만 nodeIds로 스코핑했다).
    const nodeIdSet = new Set(state.nodes.map((node) => node.id));

    const cy = cytoscape({
      container: containerRef.current,
      elements: [
        ...state.nodes.map((node) => ({
          data: {
            id: node.id,
            label: node.title,
            slug: node.slug,
            category: node.category,
          },
        })),
        ...state.edges
          .filter(
            (edge) =>
              nodeIdSet.has(edge.from_wiki_id) &&
              nodeIdSet.has(edge.to_wiki_id),
          )
          .map((edge) => ({
            data: {
              id: `${edge.from_wiki_id}->${edge.to_wiki_id}`,
              source: edge.from_wiki_id,
              target: edge.to_wiki_id,
            },
          })),
      ],
      style: [
        {
          selector: "node",
          style: {
            label: "data(label)",
            "background-color": DEFAULT_NODE_COLOR,
            color: "#222222",
            "font-size": 10,
            "text-valign": "bottom",
            "text-margin-y": 4,
            width: 24,
            height: 24,
          },
        },
        {
          selector: 'node[category = "concepts"]',
          style: { "background-color": CATEGORY_COLORS.concepts },
        },
        {
          selector: 'node[category = "entities"]',
          style: { "background-color": CATEGORY_COLORS.entities },
        },
        {
          selector: 'node[category = "guides"]',
          style: { "background-color": CATEGORY_COLORS.guides },
        },
        {
          selector: 'node[category = "maps"]',
          style: { "background-color": CATEGORY_COLORS.maps },
        },
        {
          selector: "edge",
          style: {
            width: 1,
            "line-color": "#dddddd",
            "target-arrow-color": "#dddddd",
            "target-arrow-shape": "triangle",
            "curve-style": "bezier",
          },
        },
      ],
      // wiki_links는 계층이 아니라 임의의 상호 링크(레드 링크 포함 가능한
      // 위키 전반 그래프)라 뿌리 노드를 가정하는 breadthfirst보다 힘-방향
      // cose가 이 데이터 형태에 더 맞는다 — 순환/역방향 링크가 있어도 특정
      // 루트에 종속되지 않는다.
      layout: { name: "cose" },
    });

    cy.on("tap", "node", (event) => {
      const slug = event.target.data("slug") as string;
      router.push(`/w/${workspaceId}/wiki/${slug}`);
    });

    return () => {
      cy.destroy();
    };
  }, [state, workspaceId, router]);

  if (state.status === "loading") {
    return (
      <div
        role="status"
        aria-label="그래프를 불러오는 중"
        className="flex items-center justify-center"
        style={{ minHeight: "480px" }}
      >
        <span
          aria-hidden="true"
          className="animate-spin rounded-full border-2 border-primary"
          style={{
            width: "32px",
            height: "32px",
            borderTopColor: "transparent",
          }}
        />
      </div>
    );
  }

  if (state.status === "error") {
    return (
      <p
        role="alert"
        className="text-primary-error-text"
        style={{ font: "var(--font-body-md)" }}
      >
        {LOAD_ERROR}
      </p>
    );
  }

  if (state.status === "empty") {
    return (
      <div
        className="flex flex-col items-center justify-center gap-xs text-center"
        style={{ minHeight: "480px" }}
      >
        <p className="text-ink" style={{ font: "var(--font-title-md)" }}>
          {EMPTY_HEADING}
        </p>
        <p className="text-muted" style={{ font: "var(--font-body-md)" }}>
          {EMPTY_BODY}
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-sm">
      {state.capped ? (
        <p
          role="status"
          data-testid="graph-cap-notice"
          className="text-primary-error-text"
          style={{ font: "var(--font-caption)" }}
        >
          {CAP_NOTICE}
        </p>
      ) : null}
      {/* WINDOWS #11 회피: max-w, w, h 계열 크기 유틸리티가 이 프로젝트의
          커스텀 --spacing-* @theme 오버라이드와 이름이 겹칠 위험이 있으므로,
          Cytoscape가 실제 마운트 크기를 계산할 수 있어야 하는 이 컨테이너는
          인라인 style의 리터럴 값으로 크기를 지정한다. */}
      <div
        ref={containerRef}
        data-testid="graph-canvas-container"
        style={{ width: "100%", height: "640px" }}
      />
    </div>
  );
}

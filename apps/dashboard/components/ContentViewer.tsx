"use client";

import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { GraphCanvas } from "@/components/GraphCanvas";
import { GraphLensFilter } from "@/components/GraphLensFilter";
import { WikiPageContent } from "@/components/WikiPageContent";
import { createClient } from "@/lib/supabase/client";
import { workspacePath } from "@/lib/workspace-path";
import {
  WIKI_PAGE_NOT_FOUND_HEADING,
  lookupWikiLinks,
  lookupWikiPage,
  resolveCanVerify,
  type WikiLinkRow,
  type WikiPageRow,
} from "@/lib/wiki-lookup";

export type ContentViewerTab = "wiki" | "source" | "graph" | "mindmap";

export type ContentViewerProps = { workspaceId: string };

type SourceRow = {
  id: string;
  title: string;
  source_type: string;
  created_at: string;
};

type SourceChunkRow = {
  id: string;
  raw_source_id: string;
  chunk_index: number;
  char_start: number;
  char_end: number;
  content: string;
};

const TABS: { id: ContentViewerTab; label: string }[] = [
  { id: "wiki", label: "위키 문서" },
  { id: "source", label: "원시 소스" },
  { id: "graph", label: "2D 지식 그래프" },
  { id: "mindmap", label: "마인드맵" },
];

const NO_SELECTION_TITLE = "위키 문서를 선택하세요";
const NO_SELECTION_DETAIL =
  "왼쪽 대화에서 인용을 클릭하거나, 위키 목록에서 문서를 선택하면 여기에 표시됩니다.";

/**
 * Ask 화면 우측 콘텐츠 뷰어 — 위키 문서/원시 소스/2D 지식 그래프/마인드맵
 * 4개 탭을 쿼리 파라미터(`tab`, `slug`, `category`)로 제어한다.
 * GraphLensFilter.tsx가 이미 쓰는 "URL이 상태" 패턴을 그대로 따른다.
 *
 * 관련: openspec/changes/archive/2026-08-14-add-unified-workspace-viewer
 * (unified-workspace-viewer 스펙)
 */
export function ContentViewer({ workspaceId }: ContentViewerProps) {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  const tab = (searchParams.get("tab") as ContentViewerTab | null) ?? "wiki";
  const slug = searchParams.get("slug");
  const category = searchParams.get("category");
  const chunkId = searchParams.get("chunkId");
  const tabRefs = useRef<Record<ContentViewerTab, HTMLButtonElement | null>>(
    {} as Record<ContentViewerTab, HTMLButtonElement | null>,
  );

  function setTab(nextTab: ContentViewerTab) {
    const params = new URLSearchParams(searchParams.toString());
    params.set("tab", nextTab);
    router.push(`${pathname}?${params.toString()}`);
  }

  // W3C APG 탭 패턴 — roving tabIndex(활성 탭만 0) + 방향키 이동(자동 활성화:
  // 포커스 이동과 동시에 뷰도 전환). GraphLensFilter의 칩 그룹(role="group",
  // 다중 선택 가능한 필터)과는 의도적으로 다른 시맨틱이다 — 여기는 상호
  // 배타적 뷰 전환이라 진짜 탭이다.
  function handleTabKeyDown(event: React.KeyboardEvent<HTMLButtonElement>) {
    if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
    event.preventDefault();
    const currentIndex = TABS.findIndex((item) => item.id === tab);
    const delta = event.key === "ArrowRight" ? 1 : -1;
    const nextIndex = (currentIndex + delta + TABS.length) % TABS.length;
    const nextTab = TABS[nextIndex].id;
    setTab(nextTab);
    tabRefs.current[nextTab]?.focus();
  }

  return (
    <aside className="inspect" data-od-id="citation-inspector">
      <div className="inspect-head">
        <div className="inspect-title">
          <h2>인용 인스펙터</h2>
        </div>
        <div role="tablist" aria-label="콘텐츠 뷰어" className="tabs">
          {TABS.map((item) => (
            <button
              key={item.id}
              ref={(node) => {
                tabRefs.current[item.id] = node;
              }}
              id={`content-viewer-tab-${item.id}`}
              type="button"
              role="tab"
              aria-selected={tab === item.id}
              aria-controls={`content-viewer-panel-${item.id}`}
              tabIndex={tab === item.id ? 0 : -1}
              onClick={() => setTab(item.id)}
              onKeyDown={handleTabKeyDown}
              className={`tab ${tab === item.id ? "active" : ""}`}
            >
              {item.label}
            </button>
          ))}
        </div>
      </div>

      <div className="inspect-body">
        {/* 앱은 비활성 탭을 렌더링하지 않지만 .panel.active 계약은 유지한다 —
            프로토타입과 클래스 계약이 어긋나면 프로토타입 수정이 앱에 반영되지
            않는다(섹션 13 과 같은 판정). .panel 만 붙이면 display:none 이다. */}
        <section
          id={`content-viewer-panel-${tab}`}
          role="tabpanel"
          aria-labelledby={`content-viewer-tab-${tab}`}
          tabIndex={0}
          className="panel active"
        >
          {tab === "wiki" ? (
            <WikiTab workspaceId={workspaceId} slug={slug} />
          ) : null}
          {tab === "source" ? (
            <SourceTab
              workspaceId={workspaceId}
              slug={slug}
              chunkId={chunkId}
            />
          ) : null}
          {tab === "graph" ? (
            <GraphTab workspaceId={workspaceId} category={category} />
          ) : null}
          {tab === "mindmap" ? (
            <MindmapTab
              workspaceId={workspaceId}
              slug={slug}
              category={category}
            />
          ) : null}
        </section>
      </div>
    </aside>
  );
}

/** 인스펙터의 빈 상태 · 로딩 상태 공용 조판. */
function InspectEmpty({ title, detail }: { title: string; detail: string }) {
  return (
    <div className="inspect-empty">
      <b>{title}</b>
      <span>{detail}</span>
    </div>
  );
}

function InspectLoading() {
  return (
    <p role="status" className="kicker">
      불러오는 중…
    </p>
  );
}

type WikiTabState =
  | { status: "empty" }
  | { status: "loading" }
  | { status: "not-found" }
  | {
      status: "ready";
      // ⚠️ WikiPageRow 에는 slug 가 없다(lib/wiki-lookup.ts). 리더로 넘어가는
      // 링크가 조회에 쓴 것과 정확히 같은 slug 를 쓰도록 여기 함께 담는다.
      slug: string;
      page: WikiPageRow;
      links: WikiLinkRow[];
      canVerify: boolean;
      initialBookmarked: boolean;
    };

function WikiTab({
  workspaceId,
  slug,
}: {
  workspaceId: string;
  slug: string | null;
}) {
  const [state, setState] = useState<WikiTabState>(
    slug ? { status: "loading" } : { status: "empty" },
  );

  useEffect(() => {
    if (!slug) {
      setState({ status: "empty" });
      return;
    }

    let cancelled = false;
    setState({ status: "loading" });

    async function load() {
      const supabase = createClient();
      const page = await lookupWikiPage(supabase, workspaceId, slug as string);
      if (cancelled) return;
      if (!page) {
        setState({ status: "not-found" });
        return;
      }

      const [links, canVerify, bookmark] = await Promise.all([
        lookupWikiLinks(supabase, page.id),
        resolveCanVerify(supabase, workspaceId),
        supabase
          .from("user_wiki_bookmarks")
          .select("wiki_id")
          .eq("wiki_id", page.id)
          .maybeSingle(),
      ]);
      if (cancelled) return;
      setState({
        status: "ready",
        slug: slug as string,
        page,
        links,
        canVerify,
        initialBookmarked: bookmark.data !== null,
      });
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [workspaceId, slug]);

  if (state.status === "empty") {
    return (
      <InspectEmpty title={NO_SELECTION_TITLE} detail={NO_SELECTION_DETAIL} />
    );
  }
  if (state.status === "loading") {
    return <InspectLoading />;
  }
  if (state.status === "not-found") {
    return (
      <div className="card">
        <span className="kicker">위키 문서</span>
        <h3>{WIKI_PAGE_NOT_FOUND_HEADING}</h3>
      </div>
    );
  }
  return (
    <>
      <WikiPageContent
        page={state.page}
        links={state.links}
        workspaceId={workspaceId}
        canVerify={state.canVerify}
        initialBookmarked={state.initialBookmarked}
      />
      {/* unified-workspace-viewer 「Member opens the full reader from the viewer」.
          인스펙터는 답변의 근거를 확인하는 곳이고 리더는 문서를 읽는 곳이라,
          여기서 문서 전체로 넘어갈 길이 없으면 두 화면이 끊긴다. */}
      <Link
        className="link"
        href={`${workspacePath(workspaceId)}/wiki/${state.slug}`}
      >
        위키 전체 페이지 읽기 ↗
      </Link>
    </>
  );
}

type SourceTabState =
  | { status: "empty" }
  | { status: "loading" }
  | { status: "no-sources" }
  | { status: "ready"; sources: SourceRow[] };

function SourceTab({
  workspaceId,
  slug,
  chunkId,
}: {
  workspaceId: string;
  slug: string | null;
  chunkId: string | null;
}) {
  if (chunkId) {
    return <SourceChunkView chunkId={chunkId} />;
  }

  return <SourceListTab workspaceId={workspaceId} slug={slug} />;
}

// 인용 마커(kind "source")는 위키 페이지가 아니라 특정 source_chunks 행
// 하나를 가리킨다 — CitationSidePanel이 하던 것과 같은 단건 조회를
// 그대로 재사용한다(part.id는 source_chunks.id).
function SourceChunkView({ chunkId }: { chunkId: string }) {
  const [chunk, setChunk] = useState<SourceChunkRow | null>(null);

  useEffect(() => {
    let cancelled = false;
    setChunk(null);

    async function load() {
      const supabase = createClient();
      const { data } = await supabase
        .from("source_chunks")
        .select("id,raw_source_id,chunk_index,char_start,char_end,content")
        .eq("id", chunkId)
        .single();
      if (!cancelled && data) setChunk(data as SourceChunkRow);
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [chunkId]);

  if (!chunk) {
    return <InspectLoading />;
  }

  return (
    <div className="card">
      <div className="card-top">
        <div>
          <span className="kicker">원문 청크</span>
          <h3>{`청크 #${chunk.chunk_index}`}</h3>
        </div>
      </div>
      {/* char_start–char_end 구간을 그대로 보여준다. 원문 어디에서 왔는지가
          보이지 않으면 이중 Citation 이 "출처가 있다"는 주장에 그친다. */}
      <pre className="code">
        <mark>{chunk.content}</mark>
      </pre>
      <p className="mono mt-3 text-[10px] text-[var(--muted)]">
        {`원문 좌표 ${chunk.char_start}–${chunk.char_end}`}
      </p>
    </div>
  );
}

function SourceListTab({
  workspaceId,
  slug,
}: {
  workspaceId: string;
  slug: string | null;
}) {
  const [state, setState] = useState<SourceTabState>(
    slug ? { status: "loading" } : { status: "empty" },
  );

  useEffect(() => {
    if (!slug) {
      setState({ status: "empty" });
      return;
    }

    let cancelled = false;
    setState({ status: "loading" });

    async function load() {
      const supabase = createClient();
      const { data: pageRow } = await supabase
        .from("wiki_pages")
        .select("sources")
        .eq("workspace_id", workspaceId)
        .eq("slug", slug as string)
        .single();

      const sourceIds = (pageRow?.sources ?? []) as string[];
      if (sourceIds.length === 0) {
        if (!cancelled) setState({ status: "no-sources" });
        return;
      }

      const { data: sources } = await supabase
        .from("raw_sources")
        .select("id,title,source_type,created_at")
        .eq("workspace_id", workspaceId)
        .in("id", sourceIds)
        .returns<SourceRow[]>();

      if (cancelled) return;
      setState(
        sources && sources.length > 0
          ? { status: "ready", sources }
          : { status: "no-sources" },
      );
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [workspaceId, slug]);

  if (state.status === "empty") {
    return (
      <InspectEmpty
        title="위키 문서를 선택하세요"
        detail="원시 소스는 그 문서를 만든 원문을 보여줍니다."
      />
    );
  }
  if (state.status === "loading") {
    return <InspectLoading />;
  }
  if (state.status === "no-sources") {
    return (
      <InspectEmpty
        title="연결된 원시 소스가 없습니다"
        detail="이 위키 문서에 역추적 가능한 원문 기록이 없습니다."
      />
    );
  }
  return (
    <div className="card">
      <span className="kicker">이 문서가 인용한 원문</span>
      <div className="index mt-3">
        {state.sources.map((source) => (
          <div key={source.id}>
            <Link
              href={`${workspacePath(workspaceId)}/sources/${source.id}`}
              className="min-w-0 truncate"
              title={source.title}
            >
              {source.title}
            </Link>
            <span className="tag">{source.source_type}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function GraphTab({
  workspaceId,
  category,
}: {
  workspaceId: string;
  category: string | null;
}) {
  return (
    <div className="flex flex-col gap-3">
      <section aria-label="그래프 필터" className="card">
        <span className="kicker">표시할 문서 범위</span>
        <div className="mt-2">
          <GraphLensFilter
            workspaceId={workspaceId}
            activeCategory={category}
          />
        </div>
      </section>
      <section aria-label="지식 그래프" className="card">
        <GraphCanvas workspaceId={workspaceId} category={category} />
      </section>
    </div>
  );
}

function MindmapTab({
  workspaceId,
  slug,
  category,
}: {
  workspaceId: string;
  slug: string | null;
  category: string | null;
}) {
  if (!slug) {
    return (
      <InspectEmpty
        title={NO_SELECTION_TITLE}
        detail="마인드맵은 특정 위키 문서를 중심으로 그려집니다."
      />
    );
  }
  return (
    <section aria-label="마인드맵" className="card">
      <GraphCanvas
        workspaceId={workspaceId}
        category={category}
        layoutName="breadthfirst"
        rootSlug={slug}
      />
    </section>
  );
}

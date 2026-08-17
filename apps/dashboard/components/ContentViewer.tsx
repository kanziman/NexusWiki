"use client";

import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { EmptyState } from "@/components/DashboardPrimitives";
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
    <div className="flex h-full flex-col gap-lg">
      <div
        role="tablist"
        aria-label="콘텐츠 뷰어"
        className="flex gap-xs border-b border-[var(--nw-rule)]"
      >
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
            className={`nw-focus-ring border-b-2 px-base py-sm text-sm font-medium transition-colors ${
              tab === item.id
                ? "border-[var(--nw-ink)] text-[var(--nw-ink)]"
                : "border-transparent text-[var(--nw-muted)]"
            }`}
          >
            {item.label}
          </button>
        ))}
      </div>
      <div
        id={`content-viewer-panel-${tab}`}
        role="tabpanel"
        aria-labelledby={`content-viewer-tab-${tab}`}
        tabIndex={0}
        className="flex-1"
      >
        {tab === "wiki" ? (
          <WikiTab workspaceId={workspaceId} slug={slug} />
        ) : null}
        {tab === "source" ? (
          <SourceTab workspaceId={workspaceId} slug={slug} chunkId={chunkId} />
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
      </div>
    </div>
  );
}

type WikiTabState =
  | { status: "empty" }
  | { status: "loading" }
  | { status: "not-found" }
  | {
      status: "ready";
      page: WikiPageRow;
      links: WikiLinkRow[];
      canVerify: boolean;
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

      const [links, canVerify] = await Promise.all([
        lookupWikiLinks(supabase, page.id),
        resolveCanVerify(supabase, workspaceId),
      ]);
      if (cancelled) return;
      setState({ status: "ready", page, links, canVerify });
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [workspaceId, slug]);

  if (state.status === "empty") {
    return (
      <EmptyState title={NO_SELECTION_TITLE} detail={NO_SELECTION_DETAIL} />
    );
  }
  if (state.status === "loading") {
    return (
      <p role="status" className="text-[var(--nw-muted)]">
        불러오는 중…
      </p>
    );
  }
  if (state.status === "not-found") {
    return (
      <p className="text-[var(--nw-ink)]">{WIKI_PAGE_NOT_FOUND_HEADING}</p>
    );
  }
  return (
    <WikiPageContent
      page={state.page}
      links={state.links}
      workspaceId={workspaceId}
      canVerify={state.canVerify}
    />
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
    return (
      <p role="status" className="text-[var(--nw-muted)]">
        불러오는 중…
      </p>
    );
  }

  return (
    <div className="rounded-md border border-[var(--nw-rule)] p-base">
      <p className="text-sm font-semibold text-[var(--nw-muted)]">
        {`청크 #${chunk.chunk_index} · 원문 좌표 ${chunk.char_start}–${chunk.char_end}`}
      </p>
      <mark className="bg-[var(--nw-canvas)] text-[var(--nw-body)]">
        {chunk.content}
      </mark>
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
      <EmptyState
        title="위키 문서를 선택하세요"
        detail="원시 소스는 그 문서를 만든 원문을 보여줍니다."
      />
    );
  }
  if (state.status === "loading") {
    return (
      <p role="status" className="text-[var(--nw-muted)]">
        불러오는 중…
      </p>
    );
  }
  if (state.status === "no-sources") {
    return (
      <EmptyState
        title="연결된 원시 소스가 없습니다"
        detail="이 위키 문서에 역추적 가능한 원문 기록이 없습니다."
      />
    );
  }
  return (
    <ul className="flex flex-col divide-y divide-[var(--nw-rule)]">
      {state.sources.map((source) => (
        <li key={source.id} className="py-sm">
          <Link
            href={`${workspacePath(workspaceId)}/sources/${source.id}`}
            className="nw-focus-ring text-[var(--nw-ink)] underline"
          >
            {source.title}
          </Link>
          <span className="ml-sm text-sm text-[var(--nw-muted)]">
            {source.source_type}
          </span>
        </li>
      ))}
    </ul>
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
    <div className="flex flex-col gap-base">
      <section
        aria-label="그래프 필터"
        className="rounded-sm border border-[var(--nw-rule)] bg-[var(--nw-surface)] p-base"
      >
        <p className="mb-sm text-sm font-medium text-[var(--nw-muted)]">
          표시할 문서 범위
        </p>
        <GraphLensFilter workspaceId={workspaceId} activeCategory={category} />
      </section>
      <section
        aria-label="지식 그래프"
        className="border border-[var(--nw-rule)] bg-[var(--nw-surface)] p-base sm:p-lg"
      >
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
      <EmptyState
        title={NO_SELECTION_TITLE}
        detail="마인드맵은 특정 위키 문서를 중심으로 그려집니다."
      />
    );
  }
  return (
    <section
      aria-label="마인드맵"
      className="border border-[var(--nw-rule)] bg-[var(--nw-surface)] p-base sm:p-lg"
    >
      <GraphCanvas
        workspaceId={workspaceId}
        category={category}
        layoutName="breadthfirst"
        rootSlug={slug}
      />
    </section>
  );
}

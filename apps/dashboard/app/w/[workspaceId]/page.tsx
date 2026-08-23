import { AskHero } from "@/components/AskHero";
import { KnowledgeGrid } from "@/components/KnowledgeGrid";
import { createClient } from "@/lib/supabase/server";
import { firstWikiLinkExcerpt } from "@/lib/wiki-links";

type Props = {
  params: Promise<{ workspaceId: string }>;
  searchParams?: Promise<{ category?: string }>;
};

function formatTimeAgo(dateString?: string | null): string {
  if (!dateString) return "없음";
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMinutes = Math.floor(diffMs / (1000 * 60));
  const diffHours = Math.floor(diffMinutes / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffMinutes < 1) return "방금 전";
  if (diffMinutes < 60) return `${diffMinutes}분 전`;
  if (diffHours < 24) return `${diffHours}시간 전`;
  if (diffDays < 7) return `${diffDays}일 전`;
  return date.toLocaleDateString("ko-KR", { month: "short", day: "numeric" });
}

export default async function WorkspaceHomePage({
  params,
  searchParams,
}: Props) {
  const { workspaceId } = await params;
  const { category: activeCategory } = (await searchParams) ?? {};

  const supabase = await createClient();

  const [workspaceResult, sourcesResult, pagesResult, linksResult] =
    await Promise.all([
      supabase.from("workspaces").select("name").eq("id", workspaceId).single(),
      supabase
        .from("raw_sources")
        .select("id,title,source_type,created_at")
        .eq("workspace_id", workspaceId)
        .order("created_at", { ascending: false }),
      supabase
        .from("wiki_pages")
        // ⚠️ disputed 를 함께 읽는다. 이게 빠지면 lib/verification-label.ts 의
        // 충돌 우선순위가 이 화면에서만 도달 불가능해져, 충돌 문서가 위키
        // 라이브러리에서는 "충돌 감지"인데 여기서는 "검증됨"으로 표시된다 —
        // 목적지마다 같은 상태를 다르게 부르는 바로 그 문제다.
        // ⚠️ expires_at 도 함께 읽는다. 없으면 만료된 검증이 목록에서 계속
        // "검증됨"으로 남는다 — 0007 §5 가 명시적으로 금지한 상태다.
        .select(
          "id,title,slug,category,verification_status,disputed,expires_at,sources,updated_at,content",
        )
        .eq("workspace_id", workspaceId)
        .order("updated_at", { ascending: false }),
      supabase
        .from("wiki_links")
        .select("id,target_slug,from_wiki_id,created_at")
        .eq("workspace_id", workspaceId)
        .eq("resolved", false),
    ]);

  const workspaceName = workspaceResult.data?.name ?? "워크스페이스";
  const rawSources = sourcesResult.data ?? [];
  const rawPages = (pagesResult.data ?? []) as {
    id: string;
    title: string;
    slug: string;
    category?: string | null;
    verification_status?: string | null;
    disputed?: boolean | null;
    expires_at?: string | null;
    updated_at?: string | null;
    sources?: string[] | null;
    content?: string | null;
  }[];

  const wikiPages = rawPages.map((p) => ({
    id: p.id,
    title: p.title,
    slug: p.slug,
    category: p.category,
    verification_status: p.verification_status,
    disputed: p.disputed,
    expires_at: p.expires_at,
    updated_at: p.updated_at,
    citation_count: Array.isArray(p.sources) ? p.sources.length : 0,
  }));

  const pagesMap = new Map(rawPages.map((p) => [p.id, p]));

  // Group and count unresolved links with referencing pages
  const unresolvedLinks = (linksResult.data ?? []) as {
    id?: string;
    target_slug: string;
    from_wiki_id?: string | null;
    created_at?: string;
  }[];

  const itemsMap = new Map<
    string,
    {
      target_slug: string;
      reference_count: number;
      first_detected_at: string;
      referencing_pages: {
        id: string;
        slug: string;
        title: string;
        excerpt: string | null;
      }[];
    }
  >();

  for (const link of unresolvedLinks) {
    if (!link.target_slug) continue;
    const existing = itemsMap.get(link.target_slug);
    const referringPage = link.from_wiki_id
      ? pagesMap.get(link.from_wiki_id)
      : undefined;

    if (existing) {
      existing.reference_count += 1;
      if (
        link.created_at &&
        new Date(link.created_at).getTime() <
          new Date(existing.first_detected_at).getTime()
      ) {
        existing.first_detected_at = link.created_at;
      }
      if (
        referringPage &&
        !existing.referencing_pages.some((p) => p.id === referringPage.id)
      ) {
        existing.referencing_pages.push({
          id: referringPage.id,
          slug: referringPage.slug,
          title: referringPage.title,
          excerpt: referringPage.content
            ? firstWikiLinkExcerpt(referringPage.content, link.target_slug)
            : null,
        });
      }
    } else {
      itemsMap.set(link.target_slug, {
        target_slug: link.target_slug,
        reference_count: 1,
        first_detected_at: link.created_at ?? new Date().toISOString(),
        referencing_pages: referringPage
          ? [
              {
                id: referringPage.id,
                slug: referringPage.slug,
                title: referringPage.title,
                excerpt: referringPage.content
                  ? firstWikiLinkExcerpt(
                      referringPage.content,
                      link.target_slug,
                    )
                  : null,
              },
            ]
          : [],
      });
    }
  }

  const backlogItems = Array.from(itemsMap.values()).sort(
    (a, b) => b.reference_count - a.reference_count,
  );

  const compiledCount = wikiPages.length;
  const sourcesCount = rawSources.length;
  const backlogCount = backlogItems.length;
  const latestUpdated = wikiPages[0]?.updated_at ?? null;

  return (
    <div className="content">
      {/* 1. 지식 그룹/워크스페이스 히어로 헤더 */}
      <section className="context" data-od-id="workspace-header">
        <div>
          {/* eyebrow(`워크스페이스`)를 두지 않는다 — 바로 아래 제목이 이미
              워크스페이스 이름이라 순수 중복이다. */}
          {/* 즐겨찾기는 위키 문서 단위다(user_wiki_bookmarks.wiki_id) — 이
              페이지에는 특정 wiki_id가 없어 토글할 대상이 없다. 예전 별표
              버튼은 그래서 눌러도 아무 일도 일어나지 않았다(UX-02). 실제
              토글은 WikiPageContent(위키 리더)의 title-row로 옮겼다. */}
          <div className="title-row">
            <h1 data-od-id="workspace-title">홈 대시보드</h1>
          </div>
          <p>
            연결한 원문과 컴파일된 위키를 한곳에서 질문하고, 비어 있는 지식을
            확인합니다.
          </p>
        </div>
      </section>

      {/* 2. 현황 요약 통계 */}
      <section
        className="stats"
        data-od-id="workspace-summary"
        aria-label="워크스페이스 현황"
      >
        <div className="stat">
          <b>{String(compiledCount).padStart(2, "0")}</b>
          <span>컴파일된 문서</span>
        </div>
        <div className="stat">
          <b>{String(sourcesCount).padStart(2, "0")}</b>
          <span>연결된 원문 소스</span>
        </div>
        <div className="stat">
          <b>{String(backlogCount).padStart(2, "0")}</b>
          <span>작성 대기 항목</span>
        </div>
        <div className="stat">
          <b>{formatTimeAgo(latestUpdated)}</b>
          <span>최종 업데이트</span>
        </div>
      </section>

      {/* 3. 중앙 질문창 (Ask 히어로 캔버스 + 스타터 칩) */}
      <AskHero workspaceId={workspaceId} />

      {/* 4. 2열 지식 그리드 (컴파일된 위키 + 작성 대기 백로그) */}
      <KnowledgeGrid
        workspaceId={workspaceId}
        wikiPages={wikiPages}
        backlogItems={backlogItems}
        activeCategory={activeCategory}
      />
    </div>
  );
}

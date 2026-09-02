import { BookOpen, CircleAlert, Clock, FileText } from "lucide-react";
import type { ReactNode } from "react";

import { AskHero } from "@/components/AskHero";
import { KnowledgeGrid } from "@/components/KnowledgeGrid";
import { createClient } from "@/lib/supabase/server";
import { isVerified } from "@/lib/verification-label";
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

const SUGGESTED_CHIP_LIMIT = 4;

function suggestedQuestionChips(
  pages: { title: string; citation_count: number }[],
): string[] {
  // 인용 빈도(sources 배열 길이)로만 고른다. 조회수 컬럼은 스키마에 없다.
  // 빈 배열을 넘기면 AskHero 가 하드코딩 칩을 그리지 않는다 — 기본 칩을
  // 남겨 두면 다른 도메인 워크스페이스에 엔지니어링 질문이 나타난다.
  return [...pages]
    .filter((page) => page.citation_count > 0)
    .sort((a, b) => b.citation_count - a.citation_count)
    .reduce<string[]>((chips, page) => {
      if (chips.length >= SUGGESTED_CHIP_LIMIT) return chips;
      if (chips.includes(page.title)) return chips;
      chips.push(page.title);
      return chips;
    }, []);
}

const METRIC_TAG_TONE: Record<"good" | "accent" | "warning", string> = {
  good: "bg-[var(--good)]/12 text-[var(--good)]",
  accent: "bg-[var(--soft)] text-[var(--accent)]",
  warning: "bg-[var(--warning)]/12 text-[var(--warning)]",
};

const METRIC_BAR_TONE: Record<"good" | "accent" | "warning", string> = {
  good: "bg-[var(--good)]",
  accent: "bg-[var(--accent)]",
  warning: "bg-[var(--warning)]",
};

function MetricCard({
  label,
  value,
  icon,
  tag,
  tagTone,
  progress,
  progressTone,
}: {
  label: string;
  value: string;
  icon: ReactNode;
  tag?: string;
  tagTone?: "good" | "accent" | "warning";
  progress?: number;
  progressTone?: "good" | "accent" | "warning";
}) {
  const width = progress == null ? null : Math.min(100, Math.max(0, progress));

  return (
    <div className="flex flex-col gap-2.5 overflow-hidden rounded-[14px] border border-[var(--border)] bg-[var(--surface)] px-[18px] py-4">
      <div className="flex items-center justify-between text-[12px] font-semibold text-[var(--muted)]">
        <span>{label}</span>
        <span className="text-[var(--muted)]" aria-hidden="true">
          {icon}
        </span>
      </div>
      <div className="flex items-baseline gap-2">
        <b className="font-mono text-[26px] font-extrabold tracking-tight text-[var(--fg)]">
          {value}
        </b>
        {tag && tagTone ? (
          <span
            className={`rounded-md px-1.5 py-0.5 text-[11px] font-bold ${METRIC_TAG_TONE[tagTone]}`}
          >
            {tag}
          </span>
        ) : null}
      </div>
      {width != null && progressTone ? (
        <div className="mt-1 h-1 overflow-hidden rounded-full bg-[var(--border)]">
          <div
            className={`h-full rounded-full ${METRIC_BAR_TONE[progressTone]}`}
            style={{ width: `${width}%` }}
          />
        </div>
      ) : null}
    </div>
  );
}

export default async function WorkspaceHomePage({
  params,
  searchParams,
}: Props) {
  const { workspaceId } = await params;
  const { category: activeCategory } = (await searchParams) ?? {};

  const supabase = await createClient();

  // 홈은 요청자 세션만 쓴다. workspaces 조회를 추가하지 않는다 — h1 은
  // "홈 대시보드" 고정이고 워크스페이스명은 LNB WorkspaceSwitcher 가 이미
  // 보여 준다. 이름을 한 번 더 읽으면 화면 안 명칭이 중복된다.
  const [sourcesResult, pagesResult, linksResult, chunksResult] =
    await Promise.all([
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
      // 벤토 2번 카드의 인덱싱된 청크 수. 소스 목록과 같이 workspace_id 로
      // 요청자 세션에서 읽는다. 새 RPC 를 두면 이 화면만 집계 경로가 갈라진다.
      // ⚠️ 행을 받아 .length 로 세면 PostgREST max_rows(1000)에 잘려 오류
      // 없이 항상 1000으로 고정된다. count: exact + head: true 만 정확한
      // 총수를 돌려주고, 행 페이로드도 보내지 않는다.
      supabase
        .from("source_chunks")
        .select("id", { count: "exact", head: true })
        .eq("workspace_id", workspaceId),
    ]);

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
  // ⚠️ 조회 실패나 count 부재를 0으로 접으면 "색인된 청크가 없다"로 읽힌다.
  // 이 화면의 다른 메트릭은 목록 자체가 비면 empty state 로 드러나지만,
  // 청크 수는 벤토 태그 숫자뿐이라 실패와 0을 구분하지 않으면 위장된다.
  if (chunksResult.error) {
    console.error("홈 청크 수 집계 실패", {
      workspaceId,
      error: chunksResult.error,
    });
  }
  const chunkCount =
    chunksResult.error || typeof chunksResult.count !== "number"
      ? null
      : chunksResult.count;
  const latestUpdated = wikiPages[0]?.updated_at ?? null;
  // ⚠️ isVerified 만 쓴다. verification_status === "verified" 로 세면
  // 충돌·만료 문서가 이 화면에서만 검증된 것으로 집계되어, 목적지마다
  // 같은 상태를 다르게 부르는 문제가 재발한다.
  const verifiedCount = wikiPages.filter((page) => isVerified(page)).length;
  const verificationRate =
    compiledCount === 0 ? 0 : Math.round((verifiedCount / compiledCount) * 100);
  const defaultChips = suggestedQuestionChips(wikiPages);

  return (
    <div className="content">
      {/* 1. 지식 그룹/워크스페이스 히어로 헤더 */}
      <section className="context" data-od-id="workspace-header">
        <div>
          {/* eyebrow(`워크스페이스`)를 두지 않는다 — 바로 아래 제목이 이미
              페이지 제목이라 순수 중복이다. */}
          {/* 즐겨찾기는 위키 문서 단위다(user_wiki_bookmarks.wiki_id) — 이
              페이지에는 특정 wiki_id가 없어 토글할 대상이 없다. 예전 별표
              버튼은 그래서 눌러도 아무 일도 일어나지 않았다(UX-02). 실제
              토글은 WikiPageContent(위키 리더)의 title-row로 옮겼다. */}
          <div className="title-row">
            <h1 data-od-id="workspace-title">홈 대시보드</h1>
            <span
              className="inline-flex items-center gap-1.5 rounded-full border border-[var(--good)]/30 bg-[var(--good)]/12 px-2.5 py-1 text-[11px] font-bold text-[var(--good)]"
              data-od-id="knowledge-completeness"
            >
              지식 완결도 {verificationRate}%
            </span>
          </div>
          <p>
            연결된 원문 {sourcesCount}개와 컴파일된 위키 {compiledCount}개를
            한곳에서 질문하고, 비어 있는 지식을 확인합니다.
          </p>
        </div>
      </section>

      {/* 2. 벤토 지식 건강 메트릭. 최종 업데이트는 이 요청의 서버 렌더
          스냅샷이다 — realtime 구독이 없으므로 "라이브" 카피를 붙이지 않는다. */}
      <section
        className="mt-8 mb-7 grid grid-cols-2 gap-3.5 lg:grid-cols-4"
        data-od-id="workspace-summary"
        aria-label="워크스페이스 현황"
      >
        <MetricCard
          label="컴파일된 위키"
          value={String(compiledCount).padStart(2, "0")}
          icon={<BookOpen size={16} />}
          tag={`검증률 ${verificationRate}%`}
          tagTone="good"
          progress={verificationRate}
          progressTone="good"
        />
        <MetricCard
          label="연결된 원문 소스"
          value={String(sourcesCount).padStart(2, "0")}
          icon={<FileText size={16} />}
          tag={
            chunkCount == null
              ? "인덱싱된 청크 —"
              : `인덱싱된 청크 ${chunkCount}개`
          }
          tagTone={chunkCount == null ? "warning" : "accent"}
          progress={sourcesCount > 0 ? 100 : 0}
          progressTone="accent"
        />
        <MetricCard
          label="작성 대기 지식 공백"
          value={String(backlogCount).padStart(2, "0")}
          icon={<CircleAlert size={16} />}
          tag={backlogCount > 0 ? "보완 권장" : undefined}
          tagTone={backlogCount > 0 ? "warning" : undefined}
          progress={
            backlogCount === 0 ? 0 : Math.min(100, 20 + backlogCount * 10)
          }
          progressTone="warning"
        />
        <MetricCard
          label="최종 업데이트"
          value={formatTimeAgo(latestUpdated)}
          icon={<Clock size={16} />}
        />
      </section>

      {/* 3. 중앙 질문창 (Ask 히어로 캔버스 + 스타터 칩) */}
      <AskHero workspaceId={workspaceId} defaultChips={defaultChips} />

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

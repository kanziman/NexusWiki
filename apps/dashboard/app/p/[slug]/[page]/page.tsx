import { notFound } from "next/navigation";
import { BookOpen, FileText, Globe } from "lucide-react";

import { createClient } from "@/lib/supabase/server";

type PublicWikiPageProps = {
  params: Promise<{ slug: string; page: string }>;
};

type CitationItem = {
  anchor: string;
  source_title: string;
  snippet: string;
};

export default async function PublicWikiPage({ params }: PublicWikiPageProps) {
  const { slug, page } = await params;
  const decodedSlug = decodeURIComponent(slug);
  const decodedPage = decodeURIComponent(page);

  const supabase = await createClient();

  // 1. 공개 설정 및 킬스위치 확인
  const { data: settingsData } = await supabase
    .from("workspace_public_settings")
    .select(
      "workspace_id,workspace_slug,allow_public_sharing,public_display_name,public_description",
    )
    .eq("workspace_slug", decodedSlug)
    .eq("allow_public_sharing", true)
    .maybeSingle();

  if (!settingsData) {
    notFound();
  }

  // 2. 발행된 위키 페이지 조회
  const { data: pubData } = await supabase
    .from("wiki_page_publications")
    .select(
      "published_slug,published_title,published_content,published_citations,published_at",
    )
    .eq("workspace_id", settingsData.workspace_id)
    .eq("published_slug", decodedPage)
    .maybeSingle();

  if (!pubData) {
    notFound();
  }

  const citations: CitationItem[] = Array.isArray(pubData.published_citations)
    ? (pubData.published_citations as CitationItem[])
    : [];

  const workspaceDisplayName =
    settingsData.public_display_name || settingsData.workspace_slug;

  const formattedDate = new Date(pubData.published_at).toLocaleDateString(
    "ko-KR",
    {
      year: "numeric",
      month: "long",
      day: "numeric",
    },
  );

  return (
    <div className="min-h-screen bg-[var(--bg)] text-[var(--fg)]">
      {/* 상단 공개 네비게이션 헤더 */}
      <header className="border-b border-[var(--border)] bg-[var(--surface)] px-base py-sm">
        <div className="mx-auto flex max-w-4xl items-center justify-between">
          <div className="flex items-center gap-sm">
            <Globe
              size={18}
              className="text-[var(--accent)]"
              aria-hidden="true"
            />
            <span className="font-semibold text-sm tracking-tight text-[var(--fg)]">
              {workspaceDisplayName}
            </span>
            <span className="rounded bg-[var(--surface-soft)] px-1.5 py-0.5 text-[10px] font-medium text-[var(--muted)]">
              공개 위키
            </span>
          </div>
          <div className="flex items-center gap-xs text-xs text-[var(--muted)]">
            <BookOpen size={14} aria-hidden="true" />
            <span>승인된 발행본</span>
          </div>
        </div>
      </header>

      {/* 본문 컨테이너 */}
      <main className="mx-auto flex max-w-4xl flex-col gap-xl px-base py-xxl">
        {/* 문서 헤더 */}
        <div className="flex flex-col gap-xs border-b border-[var(--border)] pb-lg">
          <div className="flex items-center gap-sm text-xs text-[var(--muted)]">
            <span>{workspaceDisplayName}</span>
            <span>/</span>
            <span className="text-[var(--fg)]">{pubData.published_title}</span>
          </div>
          <h1
            className="text-ink font-bold tracking-tight"
            style={{ font: "var(--font-title-lg)" }}
          >
            {pubData.published_title}
          </h1>
          <div className="flex items-center gap-sm text-xs text-[var(--muted)]">
            <span className="font-medium text-[var(--good)]">
              검증 및 승인됨
            </span>
            <span>·</span>
            <span>발행일: {formattedDate}</span>
          </div>
        </div>

        {/* 본문 마크다운 */}
        <article
          className="prose prose-neutral max-w-none text-body whitespace-pre-wrap leading-relaxed"
          style={{ font: "var(--font-body-md)" }}
        >
          {pubData.published_content}
        </article>

        {/* 인용된 출처 스니펫 목록 */}
        {citations.length > 0 && (
          <section
            aria-labelledby="citations-heading"
            className="mt-xl rounded-lg border border-[var(--border)] bg-[var(--surface)] p-lg"
          >
            <h2
              id="citations-heading"
              className="mb-base flex items-center gap-xs text-sm font-semibold text-[var(--fg)]"
            >
              <FileText size={16} className="text-[var(--accent)]" />
              <span>승인된 인용 출처 ({citations.length})</span>
            </h2>
            <ul className="flex flex-col gap-sm">
              {citations.map((cite, index) => (
                <li
                  key={index}
                  className="rounded border border-[var(--border)] bg-[var(--surface-soft)] p-base text-xs"
                >
                  <div className="mb-1 font-semibold text-[var(--fg)]">
                    {cite.source_title}
                  </div>
                  <p className="text-[var(--muted)] italic leading-normal">
                    &quot;{cite.snippet}&quot;
                  </p>
                </li>
              ))}
            </ul>
          </section>
        )}
      </main>
    </div>
  );
}

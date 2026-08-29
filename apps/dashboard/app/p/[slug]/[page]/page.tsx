import Image from "next/image";
import Link from "next/link";
import { notFound } from "next/navigation";

import { PublicWikiCopyLink } from "@/components/PublicWikiCopyLink";
import { PublicWikiToc } from "@/components/PublicWikiToc";
import { WikiDocumentBody } from "@/components/WikiDocumentBody";
import {
  cleanWikiContent,
  estimateReadMinutes,
  extractHeadings,
  plainCitationSnippet,
  publicWikiPath,
  workspaceInitials,
} from "@/lib/wiki-document";
import { createPublicClient } from "@/lib/supabase/public";

type PublicWikiPageProps = {
  params: Promise<{ slug: string; page: string }>;
};

type CitationItem = {
  anchor: string;
  source_title: string;
  snippet: string;
};

type PublicationRow = {
  published_slug: string;
  published_title: string;
  published_content: string;
  published_citations: unknown;
  published_at: string;
};

/**
 * PUB-02 공개 위키 라우트 — 비로그인 방문자(`anon`)가 승인된 발행본을 읽는
 * 유일한 표면이다.
 *
 * 계약: openspec/specs/public-sharing/spec.md
 * 셸: openspec/changes/align-public-wiki-reader-shell/design.md
 * 화면·쿼리 요구사항: docs/design-systems/v2/public-sharing-prd.md §3~§5
 * 불변식: PRODUCT-INVARIANTS.md §4(공개 네임스페이스) · §5(사이드카·킬스위치)
 *
 * ⚠️ 이 경로는 사이드카 두 테이블만 본다. `workspaces` · `wiki_pages` ·
 * `source_chunks` 를 조인하지 않는다 — `anon` 은 그쪽에 정책도 GRANT 도 없어서
 * 조인하는 순간 `permission denied` 로 페이지가 통째로 열리지 않는다. 사이드카가
 * 존재하는 이유가 정확히 이것이다(불변식 §4).
 */
export default async function PublicWikiPage({ params }: PublicWikiPageProps) {
  const { slug, page } = await params;
  const decodedSlug = decodeURIComponent(slug);
  const decodedPage = decodeURIComponent(page);

  // ⚠️ 요청자 세션 클라이언트를 쓰지 않는다. `/p/` 에도 세션 쿠키는 그대로
  // 실려 오는데, `authenticated` 로 실행하면 0016 의
  // `*_select_member` 정책이 킬스위치와 무관하게 행을 돌려준다 — 멤버에게만
  // 킬스위치가 무력화된다. 근거와 실측은 lib/supabase/public.ts 주석에 있다.
  const supabase = createPublicClient();

  // ⚠️ `allow_public_sharing = true` 를 여기 적지 않는다(PRD §3.1). anon 으로
  // 실행되는 한 양쪽 테이블의 RLS 가 이미 강제한다 — 앱이 같은 조건을 다시
  // 적으면 "앱이 막고 있다"는 착각이 생기고, 앱에서 빠뜨린 날 격리가 무너진다.
  // 차단은 DB 가 하되, 그 전제(anon 실행)는 위 클라이언트 선택이 보장한다.
  const { data: settingsData } = await supabase
    .from("workspace_public_settings")
    .select(
      "workspace_id,workspace_slug,public_display_name,public_description",
    )
    .eq("workspace_slug", decodedSlug)
    .maybeSingle();

  if (!settingsData) {
    notFound();
  }

  const { data: publicationRows } = await supabase
    .from("wiki_page_publications")
    .select(
      "published_slug,published_title,published_content,published_citations,published_at",
    )
    .eq("workspace_id", settingsData.workspace_id)
    .order("published_title", { ascending: true });

  const publications = (publicationRows ?? []) as PublicationRow[];
  const pubData = publications.find(
    (row) => row.published_slug === decodedPage,
  );

  // 0행이면 404다. ⚠️ 킬스위치 OFF · 미발행 · 없는 슬러그를 구분해 응답하지
  // 않는다 — 구분하는 순간 워크스페이스의 존재 여부가 밖으로 샌다(PRD §3.1).
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
    { year: "numeric", month: "long", day: "numeric" },
  );

  const sanitizedContent = cleanWikiContent(pubData.published_content);
  const headings = extractHeadings(sanitizedContent);
  const readMinutes = estimateReadMinutes(sanitizedContent);
  const related = publications
    .filter((row) => row.published_slug !== decodedPage)
    .slice(0, 4);
  const sourceTitles = citations
    .map((cite) => cite.source_title)
    .filter((title) => typeof title === "string" && title.length > 0);

  return (
    <div className="public-shell" data-od-id="public-wiki-screen">
      <header className="public-header">
        <div className="public-header-grid">
          <div className="public-header-left">
            <div className="public-brand-logo">
              <Image src="/nexuswiki-mark.png" alt="" width={18} height={18} />
            </div>
            <strong className="public-workspace-name">
              {workspaceDisplayName}
            </strong>
            <span className="public-badge">공개 위키</span>
          </div>
          <div className="public-header-center">승인된 발행본 뷰어</div>
          <div className="public-header-right">
            <PublicWikiCopyLink />
            <Link href="/signup" className="public-cta">
              시작하기
            </Link>
          </div>
        </div>
      </header>

      <div className="public-layout">
        <aside className="public-sidebar" aria-label="공개 문서">
          <div className="public-nav-head">
            <span className="public-nav-title">공개 문서</span>
            <span className="public-nav-count">{publications.length}</span>
          </div>
          <ul className="public-nav-list">
            {publications.map((row) => {
              const href = publicWikiPath(decodedSlug, row.published_slug);
              const active = row.published_slug === decodedPage;
              return (
                <li key={row.published_slug}>
                  <Link
                    href={href}
                    className={
                      active ? "public-nav-link active" : "public-nav-link"
                    }
                    aria-current={active ? "page" : undefined}
                  >
                    <FileIcon />
                    <span>{row.published_title}</span>
                  </Link>
                </li>
              );
            })}
          </ul>
        </aside>

        <main className="public-reader">
          <article className="reader">
            <nav aria-label="공개 위키 탐색 경로" className="breadcrumb-path">
              {workspaceDisplayName} / 공개 문서
            </nav>

            <div className="title-row">
              <h1>{pubData.published_title}</h1>
            </div>

            <div className="public-trust">
              <div className="public-trust-who">
                <span className="public-avatar" aria-hidden="true">
                  {workspaceInitials(workspaceDisplayName)}
                </span>
                <div>
                  <b>{workspaceDisplayName}</b>
                  {sourceTitles.length > 0 ? (
                    <span className="public-source-line">
                      <FileIcon />
                      원문 소스 · {sourceTitles[0]}
                      {sourceTitles.length > 1
                        ? ` 외 ${sourceTitles.length - 1}`
                        : ""}
                    </span>
                  ) : null}
                </div>
              </div>
              <div className="public-trust-meta">
                <span className="badge verified">검증 및 승인됨</span>
                <span className="public-read-time">
                  <ClockIcon />
                  읽기 {readMinutes}분 · {formattedDate}
                </span>
              </div>
            </div>

            <div className="article mt-7" spellCheck={false}>
              <WikiDocumentBody content={sanitizedContent} linkMode="public" />
            </div>

            {citations.length > 0 ? (
              <section
                className="pub-cites"
                aria-labelledby="citations-heading"
              >
                <h2 id="citations-heading">
                  승인된 인용 출처 ({citations.length})
                </h2>
                {/* PRD §4-2: 스니펫은 발행 시점에 사람이 구간 단위로 승인한
                    것만 들어온다. 여기서 원문을 다시 조회하지 않는다 — 조회할
                    권한 자체가 없고, 공개본은 불변 스냅샷이어야 한다. */}
                <p className="pub-cites-note">
                  발행 시점에 검토·승인된 원문 구간입니다.
                </p>
                <ul className="pub-cite-list">
                  {citations.map((cite, index) => (
                    <li key={index} className="pub-cite">
                      <b>{cite.source_title}</b>
                      <p>&quot;{plainCitationSnippet(cite.snippet)}&quot;</p>
                    </li>
                  ))}
                </ul>
              </section>
            ) : null}

            {related.length > 0 ? (
              <section
                className="public-related"
                aria-labelledby="related-heading"
              >
                <h2 id="related-heading" className="public-related-head">
                  함께 읽으면 좋은 공개 문서
                </h2>
                <div className="public-related-grid">
                  {related.map((row) => (
                    <Link
                      key={row.published_slug}
                      href={publicWikiPath(decodedSlug, row.published_slug)}
                      className="public-related-card"
                    >
                      <b>{row.published_title}</b>
                      <p>
                        {plainCitationSnippet(
                          cleanWikiContent(row.published_content),
                          90,
                        )}
                      </p>
                    </Link>
                  ))}
                </div>
              </section>
            ) : null}

            <section className="public-fork" aria-labelledby="fork-heading">
              <h2 id="fork-heading">
                내 지식도 이렇게 출처가 남은 위키로 공유해 보세요
              </h2>
              <p>
                PDF, URL, 노트를 올리면 원문과 위키를 함께 인용하는 지식
                베이스를 만듭니다.
              </p>
              <Link href="/signup" className="public-cta">
                NexusWiki 시작하기
              </Link>
            </section>
          </article>
        </main>

        <aside className="toc">
          <PublicWikiToc headings={headings} />
        </aside>
      </div>

      <footer className="public-foot">
        <b>{workspaceDisplayName}</b>
        {settingsData.public_description ? (
          <span>{settingsData.public_description}</span>
        ) : null}
        <span>
          이 페이지는 워크스페이스가 승인해 공개한 발행본입니다. 원문 파일과
          내부 문서는 공개되지 않습니다.
        </span>
      </footer>
    </div>
  );
}

function FileIcon() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      aria-hidden="true"
    >
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14 2 14 8 20 8" />
    </svg>
  );
}

function ClockIcon() {
  return (
    <svg
      width="11"
      height="11"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      aria-hidden="true"
    >
      <circle cx="12" cy="12" r="10" />
      <polyline points="12 6 12 12 16 14" />
    </svg>
  );
}

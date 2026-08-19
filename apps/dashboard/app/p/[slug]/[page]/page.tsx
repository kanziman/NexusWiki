import { notFound } from "next/navigation";
import { Fragment } from "react";

import { createPublicClient } from "@/lib/supabase/public";

type PublicWikiPageProps = {
  params: Promise<{ slug: string; page: string }>;
};

type CitationItem = {
  anchor: string;
  source_title: string;
  snippet: string;
};

/**
 * PUB-02 공개 위키 라우트 — 비로그인 방문자(`anon`)가 승인된 발행본을 읽는
 * 유일한 표면이다.
 *
 * 계약: openspec/specs/public-sharing/spec.md
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

  // ⚠️ 요청자 세션 클라이언트를 쓰지 않는다. `/p/` 는 미들웨어 matcher 밖이라
  // 세션 쿠키가 그대로 실려 오는데, `authenticated` 로 실행하면 0016 의
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

  const { data: pubData } = await supabase
    .from("wiki_page_publications")
    .select(
      "published_slug,published_title,published_content,published_citations,published_at",
    )
    .eq("workspace_id", settingsData.workspace_id)
    .eq("published_slug", decodedPage)
    .maybeSingle();

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

  const headings = extractHeadings(pubData.published_content);

  return (
    <div className="public-shell" data-od-id="public-wiki-screen">
      <header className="public-topbar">
        <div className="public-mark">
          <strong>{workspaceDisplayName}</strong>
          <span className="public-badge">공개 위키</span>
        </div>
        <span className="public-stamp">승인된 발행본</span>
      </header>

      <div className="reader-layout">
        <article className="reader">
          <nav aria-label="공개 위키 탐색 경로" className="eyebrow">
            {workspaceDisplayName} / 공개 문서
          </nav>

          <div className="title-row">
            <h1>{pubData.published_title}</h1>
          </div>

          <div className="governance">
            <span className="badge verified">검증 및 승인됨</span>
            <span className="tag">발행일 {formattedDate}</span>
          </div>

          <div className="article mt-7">
            <PublicDocumentBody content={pubData.published_content} />
          </div>

          {citations.length > 0 ? (
            <section className="pub-cites" aria-labelledby="citations-heading">
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
                    <p>&quot;{cite.snippet}&quot;</p>
                  </li>
                ))}
              </ul>
            </section>
          ) : null}
        </article>

        <aside className="toc">
          <div className="toc-heading">
            <h2>목차</h2>
          </div>
          {headings.length ? (
            <nav aria-label="이 문서에서" className="toc-list">
              {headings.map((heading) => (
                <a key={heading.id} href={`#${heading.id}`}>
                  {heading.title}
                </a>
              ))}
            </nav>
          ) : (
            <p className="m-0 text-[11px] text-[var(--muted)]">
              제목이 없는 문서입니다.
            </p>
          )}
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

/** 제목 줄만 뽑아 목차를 만든다. 내부 리더(WikiPageContent)와 같은 규칙이다. */
function extractHeadings(content: string) {
  return content.split("\n").flatMap((line, index) => {
    const match = /^(#{1,3})\s+(.+?)\s*$/.exec(line);
    return match
      ? [{ id: `section-${index}`, title: stripWikiLinks(match[2]) }]
      : [];
  });
}

/**
 * `[[문서명]]` 을 제목 평문으로 펼친다 — 링크는 만들지 않는다.
 * ⚠️ 근거: PRODUCT-INVARIANTS.md §4 「공개 표면에서 내부 라우트로 링크하지 않음」.
 */
function stripWikiLinks(text: string): string {
  return text.replace(/\[\[([^\]]+)\]\]/g, (_match, inner: string) => {
    const [target] = inner.split("|");
    return target.trim();
  });
}

/** 발행 본문 조판. 내부 리더와 같은 제목 레벨 규칙을 쓴다(h2/h3/h4). */
function PublicDocumentBody({ content }: { content: string }) {
  const lines = content.split("\n");

  return (
    <>
      {lines.map((line, index) => {
        const heading = /^(#{1,3})\s+(.+?)\s*$/.exec(line);

        if (heading) {
          const Tag =
            heading[1].length === 1
              ? "h2"
              : heading[1].length === 2
                ? "h3"
                : "h4";
          return (
            <Tag key={index} id={`section-${index}`} className="scroll-mt-6">
              {stripWikiLinks(heading[2])}
            </Tag>
          );
        }

        if (line.trim().length === 0) {
          return <Fragment key={index} />;
        }

        return <p key={index}>{stripWikiLinks(line)}</p>;
      })}
    </>
  );
}

import { WikiPageContent } from "@/components/WikiPageContent";
import {
  WIKI_PAGE_NOT_FOUND_HEADING,
  lookupWikiBookmark,
  lookupWikiLinks,
  lookupWikiPage,
  lookupWikiPublication,
  lookupWorkspaceSlug,
  resolveCanVerify,
} from "@/lib/wiki-lookup";
import { createClient } from "@/lib/supabase/server";

type WikiPageRouteProps = {
  params: Promise<{ workspaceId: string; slug: string }>;
};

/**
 * UI-05 위키 상세 라우트 — Server Component로 요청자 세션(RLS)을 통해
 * 페이지를 읽고 이 라우트에서 리더를 직접 렌더링한다.
 *
 * ⚠️ 예전에는 여기서 `/ask?slug=…&tab=wiki`로 리다이렉트했다. 그러면
 * wiki-document-reader-prd.md §2.4가 요구하는 우측 목차 패널이 들어갈 자리가
 * 통합 뷰어에 없어, 리더 화면 자체가 앱에 존재하지 않게 된다 —
 * openspec/changes/restore-standalone-wiki-reader 참조. 통합 뷰어의 위키 탭은
 * 그대로 남는다: 그쪽은 답변의 근거를 확인하는 자리고, 여기는 문서를 읽는
 * 자리다.
 *
 * 설계 근거: supabase/migrations/0004_rls_policies.sql 섹션 6/7
 *            (wiki_pages_select_member, wiki_links_select_member)
 */
export default async function WikiPageRoute({ params }: WikiPageRouteProps) {
  const { workspaceId, slug } = await params;
  const normalizedSlug = normalizeRouteSlug(slug);

  if (!normalizedSlug) {
    return <WikiPageNotFound />;
  }

  const supabase = await createClient();
  const page = await lookupWikiPage(supabase, workspaceId, normalizedSlug);

  if (!page) {
    // 이미 workspace_id로 스코프된 조회다 — 남의 워크스페이스 존재 여부를
    // 흘리는 D-12 no-enumeration 케이스가 아니라, 그냥 "이 슬러그는 없다"는
    // 같은 테넌트 내부 사실이다. 원문 오류를 노출하지 않고 고정 문구만
    // 보여준다.
    return <WikiPageNotFound />;
  }

  const [links, canVerify, bookmarked, workspaceSlug, publication] =
    await Promise.all([
      lookupWikiLinks(supabase, page.id),
      resolveCanVerify(supabase, workspaceId),
      lookupWikiBookmark(supabase, page.id),
      lookupWorkspaceSlug(supabase, workspaceId),
      lookupWikiPublication(supabase, page.id),
    ]);

  return (
    <WikiPageContent
      page={page}
      links={links}
      workspaceId={workspaceId}
      workspaceSlug={workspaceSlug ?? ""}
      canVerify={canVerify}
      initialBookmarked={bookmarked}
      initialPublishedSlug={publication?.published_slug ?? null}
    />
  );
}

function normalizeRouteSlug(slug: string): string | null {
  try {
    return decodeURIComponent(slug);
  } catch {
    return null;
  }
}

function WikiPageNotFound() {
  return <p className="reader">{WIKI_PAGE_NOT_FOUND_HEADING}</p>;
}

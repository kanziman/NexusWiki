import { redirect } from "next/navigation";

import { lookupWikiPage, WIKI_PAGE_NOT_FOUND_HEADING } from "@/lib/wiki-lookup";
import { workspacePath } from "@/lib/workspace-path";
import { createClient } from "@/lib/supabase/server";

type WikiPageRouteProps = {
  params: Promise<{ workspaceId: string; slug: string }>;
};

/**
 * UI-05 위키 상세 라우트 — Server Component로 요청자 세션(RLS)을 통해
 * 페이지 존재를 확인한 뒤, 통합 워크스페이스 뷰어(`/ask`)로 리다이렉트한다
 * (openspec/changes/archive/2026-08-14-add-unified-workspace-viewer,
 * wiki-page-routing 스펙의 "Legacy wiki route redirects into the unified
 * viewer" 시나리오). 존재 확인 자체는 리다이렉트 이전에 반드시 실행해야
 * malformed/cross-workspace 시나리오가 기존과 동일하게 유지된다 — 확인 없이
 * 무조건 리다이렉트하면 없는 페이지도 통합 뷰로 넘어가 버린다.
 *
 * 관련 태스크: 06-07-PLAN.md Task 3
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

  redirect(
    `${workspacePath(workspaceId)}/ask?slug=${encodeURIComponent(normalizedSlug)}&tab=wiki`,
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
  return (
    <p className="text-ink" style={{ font: "var(--font-title-md)" }}>
      {WIKI_PAGE_NOT_FOUND_HEADING}
    </p>
  );
}

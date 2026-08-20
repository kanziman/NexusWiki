import type { SupabaseClient } from "@supabase/supabase-js";

// UI-SPEC Copywriting Contract — 문구를 한 글자도 바꾸지 않는다. wiki/[slug]/
// page.tsx(서버, not-found 판정)와 ContentViewer(클라이언트, 통합 뷰 렌더링)
// 양쪽이 같은 문구를 쓰도록 여기서 공유한다.
export const WIKI_PAGE_NOT_FOUND_HEADING = "페이지를 찾을 수 없습니다";

export type WikiPageRow = {
  id: string;
  title: string;
  content: string;
  category: string;
  verification_status: string;
  verified_by: string | null;
  verified_at: string | null;
  expires_at: string | null;
  disputed: boolean;
};

export type WikiLinkRow = { target_slug: string; resolved: boolean };

/**
 * wiki/[slug]/page.tsx(서버, not-found 판정용)와 ContentViewer(클라이언트,
 * 통합 뷰 렌더링용) 양쪽이 같은 조회 로직을 쓰도록 공유한다 — wiki-page-routing
 * 스펙의 "동일한 slug 디코딩·조회"가 진입 경로와 무관하게 유지돼야 하므로.
 */
export async function lookupWikiPage(
  supabase: SupabaseClient,
  workspaceId: string,
  slug: string,
): Promise<WikiPageRow | null> {
  const { data, error } = await supabase
    .from("wiki_pages")
    .select(
      "id,title,content,category,verification_status,verified_by,verified_at,expires_at,disputed",
    )
    .eq("workspace_id", workspaceId)
    .eq("slug", slug)
    .single();

  if (error || !data) return null;
  return data as WikiPageRow;
}

export async function lookupWikiLinks(
  supabase: SupabaseClient,
  fromWikiId: string,
): Promise<WikiLinkRow[]> {
  const { data } = await supabase
    .from("wiki_links")
    .select("target_slug,resolved")
    .eq("from_wiki_id", fromWikiId);

  return data ?? [];
}

/**
 * 요청자 본인이 이 위키 문서를 즐겨찾기했는지 — wiki/[slug]/page.tsx(서버)와
 * ContentViewer(클라이언트) 양쪽이 같은 조회를 쓰도록 공유한다. RLS
 * (user_wiki_bookmarks_select_own)가 본인 행으로만 좁혀 주므로 user_id
 * 필터는 필요 없다.
 */
export async function lookupWikiBookmark(
  supabase: SupabaseClient,
  wikiId: string,
): Promise<boolean> {
  const { data } = await supabase
    .from("user_wiki_bookmarks")
    .select("wiki_id")
    .eq("wiki_id", wikiId)
    .maybeSingle();

  return data !== null;
}

/**
 * editor 이상 여부 판정 — RPC 우선, 실패 시 자신의 workspace_members 행을
 * 직접 읽는 폴백. wiki/[slug]/page.tsx의 resolveCanVerify와 동일한 로직을
 * 공유한다 (⚠️ UX 편의 판정일 뿐, 실제 쓰기 권한 경계는 RLS다).
 */
export async function resolveCanVerify(
  supabase: SupabaseClient,
  workspaceId: string,
): Promise<boolean> {
  const { data, error } = await supabase.rpc("has_workspace_role", {
    ws_id: workspaceId,
    min_role: "editor",
  });
  if (!error && typeof data === "boolean") {
    return data;
  }

  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return false;

  const { data: memberRow } = await supabase
    .from("workspace_members")
    .select("role")
    .eq("workspace_id", workspaceId)
    .eq("user_id", user.id)
    .single();

  return memberRow ? ["owner", "editor"].includes(memberRow.role) : false;
}

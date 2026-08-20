"use server";

import { createClient } from "@/lib/supabase/server";

type ToggleBookmarkResult = { bookmarked: boolean } | { error: string };

// requester JWT로 직접 읽고 쓴다 — RLS(user_wiki_bookmarks_select_own 등)가
// 요청자 본인 소유 행으로만 좁혀 준다. service_client는 쓰지 않는다.
export async function toggleWikiBookmark(
  wikiId: string,
  workspaceId: string,
): Promise<ToggleBookmarkResult> {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return { error: "로그인이 필요합니다." };

  const { data: existing } = await supabase
    .from("user_wiki_bookmarks")
    .select("wiki_id")
    .eq("wiki_id", wikiId)
    .maybeSingle();

  if (existing) {
    const { error } = await supabase
      .from("user_wiki_bookmarks")
      .delete()
      .eq("wiki_id", wikiId);
    if (error) return { error: "즐겨찾기를 해제하지 못했습니다." };
    return { bookmarked: false };
  }

  const { error } = await supabase.from("user_wiki_bookmarks").insert({
    user_id: user.id,
    wiki_id: wikiId,
    workspace_id: workspaceId,
  });
  if (error) return { error: "즐겨찾기에 추가하지 못했습니다." };
  return { bookmarked: true };
}

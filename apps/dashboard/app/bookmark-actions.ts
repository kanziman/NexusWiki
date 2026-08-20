"use server";

import { createClient } from "@/lib/supabase/server";

type SetBookmarkResult = { bookmarked: boolean } | { error: string };

// requester JWT로 직접 읽고 쓴다 — RLS(user_wiki_bookmarks_select_own 등)가
// 요청자 본인 소유 행으로만 좁혀 준다. service_client는 쓰지 않는다.
//
// ⚠️ 읽고-분기하고-쓰는 toggle이 아니라, 클라이언트가 원하는 최종 상태를
// 그대로 받아 멱등하게 반영한다. 같은 문서를 두 탭에서 열어두고 둘 다
// 빠르게 클릭하면(탭 A가 추가한 직후 탭 B의 "추가" 클릭이 도착) read-then-
// branch 방식은 탭 B가 "이미 있음"을 보고 반대로 삭제해버리는 경쟁이
// 생긴다 — upsert(ignoreDuplicates)/delete는 둘 다 그 자체로 멱등해
// 이 경쟁이 없다.
export async function setWikiBookmark(
  wikiId: string,
  workspaceId: string,
  bookmarked: boolean,
): Promise<SetBookmarkResult> {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return { error: "로그인이 필요합니다." };

  if (bookmarked) {
    const { error } = await supabase
      .from("user_wiki_bookmarks")
      .upsert(
        { user_id: user.id, wiki_id: wikiId, workspace_id: workspaceId },
        { onConflict: "user_id,wiki_id", ignoreDuplicates: true },
      );
    if (error) return { error: "즐겨찾기에 추가하지 못했습니다." };
    return { bookmarked: true };
  }

  const { error } = await supabase
    .from("user_wiki_bookmarks")
    .delete()
    .eq("wiki_id", wikiId);
  if (error) return { error: "즐겨찾기를 해제하지 못했습니다." };
  return { bookmarked: false };
}

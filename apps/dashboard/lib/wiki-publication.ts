import type { SupabaseClient } from "@supabase/supabase-js";

import { plainCitationSnippet } from "@/lib/wiki-document";

export type WikiPublicationSnapshot = {
  published_slug: string;
};

/**
 * 검증된 위키의 현재 본문·인용을 `wiki_page_publications`에 스냅샷한다.
 *
 * 대시보드가 배포된 FastAPI가 아니라 요청자 세션 클라이언트로 쓰는 이유:
 * 공개 설정(`PublicSharingSettings`)과 같은 사이드카 쓰기 경로다. RLS와
 * `enforce_publication_verified`가 게이트다.
 *
 * 설계 근거: openspec/changes/add-wiki-page-publish-controls/design.md
 */
export async function publishWikiPage(
  supabase: SupabaseClient,
  params: { workspaceId: string; wikiId: string; userId: string },
): Promise<WikiPublicationSnapshot> {
  const { data: page, error: pageError } = await supabase
    .from("wiki_pages")
    .select(
      "slug,title,content,sources,verification_status,expires_at,disputed",
    )
    .eq("id", params.wikiId)
    .eq("workspace_id", params.workspaceId)
    .single();

  if (pageError || !page) {
    throw new Error("publish_forbidden");
  }
  if (page.disputed === true || isExpired(page.expires_at)) {
    throw new Error("publish_forbidden");
  }

  const citations = await citationSnapshot(
    supabase,
    params.workspaceId,
    sourceIds(page.sources),
  );

  // ⚠️ representation을 요구하지 않는다. upsert 기본 Prefer는 return=minimal
  // 이라 data가 null이다. slug는 방금 읽은 페이지에서 이미 알고 있다 — 빈
  // representation을 실패로 보면 INSERT는 커밋된 채로 화면만 에러가 된다.
  const { error } = await supabase.from("wiki_page_publications").upsert(
    {
      wiki_page_id: params.wikiId,
      workspace_id: params.workspaceId,
      published_slug: page.slug,
      published_title: page.title,
      published_content: page.content,
      published_citations: citations,
      published_by: params.userId,
      published_at: new Date().toISOString(),
    },
    { onConflict: "wiki_page_id" },
  );

  if (error) {
    throw new Error("publish_forbidden");
  }
  return { published_slug: page.slug };
}

export async function unpublishWikiPage(
  supabase: SupabaseClient,
  params: { workspaceId: string; wikiId: string },
): Promise<void> {
  const { error } = await supabase
    .from("wiki_page_publications")
    .delete()
    .eq("wiki_page_id", params.wikiId)
    .eq("workspace_id", params.workspaceId);

  if (error) {
    throw new Error("unpublish_forbidden");
  }
}

export function sourceIds(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.filter(
    (item): item is string => typeof item === "string" && item.length > 0,
  );
}

export function isExpired(value: unknown): boolean {
  if (typeof value !== "string" || !value) return false;
  const parsed = Date.parse(value);
  return Number.isFinite(parsed) && parsed < Date.now();
}

async function citationSnapshot(
  supabase: SupabaseClient,
  workspaceId: string,
  ids: string[],
): Promise<{ anchor: string; source_title: string; snippet: string }[]> {
  const citations: { anchor: string; source_title: string; snippet: string }[] =
    [];
  for (const sourceId of ids) {
    const { data: sources } = await supabase
      .from("raw_sources")
      .select("id,title")
      .eq("id", sourceId)
      .eq("workspace_id", workspaceId)
      .limit(1);
    const source = Array.isArray(sources) ? sources[0] : null;
    if (!source) continue;

    const { data: chunks } = await supabase
      .from("source_chunks")
      .select("content,chunk_index")
      .eq("raw_source_id", sourceId)
      .eq("workspace_id", workspaceId)
      .order("chunk_index", { ascending: true })
      .limit(1);
    const chunk = Array.isArray(chunks) ? chunks[0] : null;
    const content = typeof chunk?.content === "string" ? chunk.content : "";
    citations.push({
      anchor: sourceId,
      source_title:
        typeof source.title === "string" && source.title
          ? source.title
          : "원문",
      snippet: plainCitationSnippet(content),
    });
  }
  return citations;
}

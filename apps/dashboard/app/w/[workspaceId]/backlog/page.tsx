import { BacklogItem, BacklogList } from "@/components/BacklogList";
import { createClient } from "@/lib/supabase/server";

type BacklogPageProps = {
  params: Promise<{ workspaceId: string }>;
};

/**
 * UI-06 백로그 라우트 — Server Component로 요청자 세션(RLS)을 통해
 * 미해결 레드링크(to_wiki_id IS NULL)를 조회하고 주제별로 집계하여 전달한다.
 */
export default async function BacklogPage({ params }: BacklogPageProps) {
  const { workspaceId } = await params;
  const supabase = await createClient();

  // 1. 미해결 위키 링크 조회
  const { data: linksData } = await supabase
    .from("wiki_links")
    .select("id,target_slug,from_wiki_id,created_at")
    .eq("workspace_id", workspaceId)
    .is("to_wiki_id", null);

  // 2. 출발지 위키 페이지 정보 조회
  const { data: pagesData } = await supabase
    .from("wiki_pages")
    .select("id,slug,title")
    .eq("workspace_id", workspaceId);

  const pagesMap = new Map<string, { id: string; slug: string; title: string }>(
    (pagesData ?? []).map((page) => [page.id, page]),
  );

  const itemsMap = new Map<
    string,
    {
      target_slug: string;
      impact: number;
      first_detected_at: string;
      referencing_pages: { id: string; slug: string; title: string }[];
    }
  >();

  for (const link of linksData ?? []) {
    const existing = itemsMap.get(link.target_slug);
    const referringPage = link.from_wiki_id
      ? pagesMap.get(link.from_wiki_id)
      : undefined;

    if (existing) {
      existing.impact += 1;
      if (
        new Date(link.created_at).getTime() <
        new Date(existing.first_detected_at).getTime()
      ) {
        existing.first_detected_at = link.created_at;
      }
      if (
        referringPage &&
        !existing.referencing_pages.some((p) => p.id === referringPage.id)
      ) {
        existing.referencing_pages.push(referringPage);
      }
    } else {
      itemsMap.set(link.target_slug, {
        target_slug: link.target_slug,
        impact: 1,
        first_detected_at: link.created_at,
        referencing_pages: referringPage ? [referringPage] : [],
      });
    }
  }

  const items: BacklogItem[] = Array.from(itemsMap.values()).sort(
    (a, b) =>
      b.impact - a.impact ||
      new Date(a.first_detected_at).getTime() -
        new Date(b.first_detected_at).getTime(),
  );

  return <BacklogList workspaceId={workspaceId} initialItems={items} />;
}

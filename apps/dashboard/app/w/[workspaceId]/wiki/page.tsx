import { WikiLibrary } from "@/components/WikiLibrary";
import { createClient } from "@/lib/supabase/server";

type WikiIndexPageProps = {
  params: Promise<{ workspaceId: string }>;
};

/**
 * UI-05 위키 인덱스 라우트 — `WorkspaceSidebar`의 "위키 문서" 링크가 가리키는 목록 화면.
 * Server Component가 요청자 세션(RLS `wiki_pages_select_member`)으로 직접
 * 읽는다 — apps/api를 거치지 않는다(sources/page.tsx와 같은 패턴).
 *
 * 관련 태스크: 06-07-PLAN.md Task 3
 */
export default async function WikiIndexPage({ params }: WikiIndexPageProps) {
  const { workspaceId } = await params;
  const supabase = await createClient();

  const { data } = await supabase
    .from("wiki_pages")
    .select("id,slug,title,category,content,verification_status,disputed")
    .eq("workspace_id", workspaceId)
    .order("title");

  const pages = data ?? [];

  // ⚠️ 빈 상태를 여기서 가로채지 않는다. 예전에는 pages.length === 0 일 때
  // 라우트가 자체 마크업을 반환해 WikiLibrary 에 아예 도달하지 않았고, 그래서
  // 화면이 페이지 프레임 없이 문장 두 줄로만 렌더링됐다 — v2 이식 후에도 그
  // 분기만 v1 로 남아 있었다. 빈 상태도 이 화면의 상태 중 하나이므로
  // 컴포넌트가 함께 소유한다.
  return <WikiLibrary pages={pages} workspaceId={workspaceId} />;
}

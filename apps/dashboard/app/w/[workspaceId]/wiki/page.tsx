import { WikiLibrary } from "@/components/WikiLibrary";
import { createClient } from "@/lib/supabase/server";

type WikiIndexPageProps = {
  params: Promise<{ workspaceId: string }>;
};

// UI-SPEC Copywriting Contract "Empty wiki (no pages yet)" — 문구를 한 글자도
// 바꾸지 않는다.
const EMPTY_HEADING = "아직 컴파일된 위키 페이지가 없습니다";
const EMPTY_BODY = "소스를 추가하면 자동으로 위키 페이지가 생성됩니다.";

/**
 * UI-05 위키 인덱스 라우트 — `NavShell`의 "위키" 링크가 가리키는 목록 화면.
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

  if (pages.length === 0) {
    return (
      <div className="flex flex-col gap-xs">
        <p className="text-ink" style={{ font: "var(--font-title-md)" }}>
          {EMPTY_HEADING}
        </p>
        <p className="text-muted" style={{ font: "var(--font-body-sm)" }}>
          {EMPTY_BODY}
        </p>
      </div>
    );
  }

  return <WikiLibrary pages={pages} workspaceId={workspaceId} />;
}

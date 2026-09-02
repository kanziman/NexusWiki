import { WikiLibrary } from "@/components/WikiLibrary";
import { createClient } from "@/lib/supabase/server";

type WikiIndexPageProps = {
  params: Promise<{ workspaceId: string }>;
  searchParams?: Promise<{ bookmarked?: string }>;
};

/**
 * UI-05 위키 인덱스 라우트 — `WorkspaceSidebar`의 "위키 문서" 링크가 가리키는 목록 화면.
 * Server Component가 요청자 세션(RLS `wiki_pages_select_member`)으로 직접
 * 읽는다 — apps/api를 거치지 않는다(sources/page.tsx와 같은 패턴).
 *
 * `?bookmarked=true`는 LNB "즐겨찾기" 링크가 붙이는 필터다(UX-02). 필터링은
 * 여기 라우트에서만 하고 WikiLibrary 자체의 props·필터 계약(스펙:
 * wiki-library-navigation)은 건드리지 않는다 — 이미 만들어진 pages 배열을
 * 좁혀서 넘길 뿐이다.
 *
 * 관련 태스크: 06-07-PLAN.md Task 3
 */
export default async function WikiIndexPage({
  params,
  searchParams,
}: WikiIndexPageProps) {
  const { workspaceId } = await params;
  const resolvedSearchParams = searchParams ? await searchParams : {};
  const bookmarkedOnly = resolvedSearchParams.bookmarked === "true";
  const supabase = await createClient();

  // ⚠️ expires_at 을 빼지 않는다 — 빼면 만료된 검증이 목록·통계에서 계속
  // "검증됨"으로 잡힌다(0007 §5: "만료된 검증을 검증으로 세면 오래된 위키가
  // 영원히 verified 로 남습니다").
  // sources 는 행 인용 수(배열 길이)용이다. 조회수 컬럼은 스키마에 없고,
  // 새 RPC 를 만들면 사용자 경로가 service_role 쪽으로 새기 쉽다.
  // 즐겨찾기 분기와 전체 조회가 이 문자열 하나만 쓰게 해 두 경로가
  // 어긋나지 않게 한다.
  const pageColumns =
    "id,slug,title,category,content,verification_status,disputed,expires_at,sources";
  let pages: {
    id: string;
    slug: string;
    title: string;
    category: string;
    content: string;
    verification_status: string;
    disputed: boolean;
    expires_at?: string | null;
    sources?: unknown;
  }[];

  if (bookmarkedOnly) {
    // 즐겨찾기 개수만큼만 wiki_pages를 읽는다 — 전체를 읽어와 content까지
    // 내려받은 뒤 JS에서 걸러내면, 즐겨찾기가 소수여도 워크스페이스 전체
    // 문서 본문을 매번 통째로 전송하게 된다.
    const { data: bookmarks } = await supabase
      .from("user_wiki_bookmarks")
      .select("wiki_id")
      .eq("workspace_id", workspaceId);
    const bookmarkedIds = (bookmarks ?? []).map((b) => b.wiki_id);

    if (bookmarkedIds.length === 0) {
      pages = [];
    } else {
      const { data } = await supabase
        .from("wiki_pages")
        .select(pageColumns)
        .eq("workspace_id", workspaceId)
        .in("id", bookmarkedIds)
        .order("title");
      pages = data ?? [];
    }
  } else {
    const { data } = await supabase
      .from("wiki_pages")
      .select(pageColumns)
      .eq("workspace_id", workspaceId)
      .order("title");
    pages = data ?? [];
  }

  let user = null;
  if (supabase.auth?.getUser) {
    const { data } = await supabase.auth.getUser();
    user = data?.user ?? null;
  }

  const { data: member } = user
    ? await supabase
        .from("workspace_members")
        .select("role")
        .eq("workspace_id", workspaceId)
        .eq("user_id", user.id)
        .maybeSingle()
    : { data: null };

  const canVerify = member?.role === "owner" || member?.role === "editor";
  const isOwner = member?.role === "owner";

  // ⚠️ 빈 상태를 여기서 가로채지 않는다. 예전에는 pages.length === 0 일 때
  // 라우트가 자체 마크업을 반환해 WikiLibrary 에 아예 도달하지 않았고, 그래서
  // 화면이 페이지 프레임 없이 문장 두 줄로만 렌더링됐다 — v2 이식 후에도 그
  // 분기만 v1 로 남아 있었다. 빈 상태도 이 화면의 상태 중 하나이므로
  // 컴포넌트가 함께 소유한다.
  return (
    <WikiLibrary
      pages={pages}
      workspaceId={workspaceId}
      canVerify={canVerify}
      isOwner={isOwner}
    />
  );
}

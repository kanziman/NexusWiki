import { WikiPageContent } from "@/components/WikiPageContent";
import { createClient } from "@/lib/supabase/server";

type WikiPageRouteProps = {
  params: Promise<{ workspaceId: string; slug: string }>;
};

// 이 화면 전용 문구 — UI-SPEC Copywriting Contract에 없는 자리라 이 파일이
// 소유한다(같은 슬러그 조회 실패라도 D-12 no-enumeration 대상은 아니다 — 아래
// 주석 참조).
const PAGE_NOT_FOUND_HEADING = "페이지를 찾을 수 없습니다";

type SupabaseServerClient = Awaited<ReturnType<typeof createClient>>;

/**
 * UI-05 위키 상세 라우트 — Server Component로 요청자 세션(RLS)을 통해
 * `wiki_pages`/`wiki_links`를 직접 읽고 `WikiPageContent`(클라이언트
 * 컴포넌트)에 위임한다.
 *
 * 관련 태스크: 06-07-PLAN.md Task 3
 * 설계 근거: supabase/migrations/0004_rls_policies.sql 섹션 6/7
 *            (wiki_pages_select_member, wiki_links_select_member)
 */
export default async function WikiPageRoute({ params }: WikiPageRouteProps) {
  const { workspaceId, slug } = await params;
  const supabase = await createClient();

  const { data: page, error } = await supabase
    .from("wiki_pages")
    .select(
      "id,title,content,verification_status,verified_by,verified_at,expires_at,disputed",
    )
    .eq("workspace_id", workspaceId)
    .eq("slug", slug)
    .single();

  if (error || !page) {
    // 이미 `.eq("workspace_id", workspaceId)`로 호출자 자신의 워크스페이스로
    // 스코프된 조회다 — 남의 워크스페이스 존재 여부를 흘리는 D-12
    // no-enumeration 케이스가 아니라, 그냥 "이 슬러그는 없다"는 같은
    // 테넌트 내부 사실이다. 원문 오류를 노출하지 않고 고정 문구만 보여준다.
    return (
      <p className="text-ink" style={{ font: "var(--font-title-md)" }}>
        {PAGE_NOT_FOUND_HEADING}
      </p>
    );
  }

  const { data: links } = await supabase
    .from("wiki_links")
    .select("target_slug,resolved")
    .eq("from_wiki_id", page.id);

  const canVerify = await resolveCanVerify(supabase, workspaceId);

  return (
    <WikiPageContent
      page={page}
      links={links ?? []}
      workspaceId={workspaceId}
      canVerify={canVerify}
    />
  );
}

/**
 * editor 이상 여부를 서버에서 판정한다 — `has_workspace_role` RPC(0004
 * `grant execute ... to authenticated`)를 우선 쓰고, RPC가 어떤 이유로든 쓸 수
 * 없으면 호출자 자신의 `workspace_members` 행(SELECT는 항상 허용,
 * `workspace_members_select_member`)을 직접 읽어 역할을 비교한다.
 *
 * ⚠️ 이 판정은 UX 편의(버튼 노출 여부)일 뿐이다 — 실제 쓰기 권한 경계는
 * `wiki.py`의 verify 엔드포인트가 태우는 RLS(`wiki_pages_update_editor`)다
 * (T-06-21).
 */
async function resolveCanVerify(
  supabase: SupabaseServerClient,
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

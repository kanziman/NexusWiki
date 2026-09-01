import { SourceDetailContent } from "@/components/SourceDetailContent";
import { createClient } from "@/lib/supabase/server";

type SourceDetailRouteProps = {
  params: Promise<{ workspaceId: string; id: string }>;
};

const SOURCE_NOT_FOUND_HEADING = "자료를 찾을 수 없습니다";
const SOURCE_LOAD_ERROR_HEADING =
  "자료를 불러오지 못했습니다. 잠시 후 다시 시도해주세요.";

/**
 * 자료 상세 라우트 — Server Component로 요청자 세션(RLS)을 통해
 * 원문 메타데이터, 추출된 청크, 인용된 위키 문서 목록을 한 번에 조회하여
 * SourceDetailContent(클라이언트 컴포넌트)로 전달한다.
 *
 * 설계 근거: supabase/migrations/0004_rls_policies.sql 섹션 5/6/7
 *            (raw_sources_select_member, source_chunks_select_member, wiki_pages_select_member)
 */
export default async function SourceDetailRoute({
  params,
}: SourceDetailRouteProps) {
  const { workspaceId, id } = await params;

  const supabase = await createClient();

  let user = null;
  if (supabase.auth?.getUser) {
    const { data } = await supabase.auth.getUser();
    user = data?.user ?? null;
  }

  const [sourceResult, chunksResult, wikiResult, memberResult] =
    await Promise.all([
      supabase
        .from("raw_sources")
        .select(
          "id,title,source_type,mime_type,byte_size,content_hash,created_at,content",
        )
        .eq("workspace_id", workspaceId)
        .eq("id", id)
        .maybeSingle(),
      supabase
        .from("source_chunks")
        .select("id,raw_source_id,chunk_index,char_start,char_end,content")
        .eq("workspace_id", workspaceId)
        .eq("raw_source_id", id)
        .order("chunk_index", { ascending: true }),
      supabase
        .from("wiki_pages")
        .select("id,title,slug,category,sources")
        .eq("workspace_id", workspaceId),
      user
        ? supabase
            .from("workspace_members")
            .select("role")
            .eq("workspace_id", workspaceId)
            .eq("user_id", user.id)
            .maybeSingle()
        : Promise.resolve({ data: null, error: null }),
    ]);

  if (sourceResult.error) {
    console.error("소스 상세 조회 실패", {
      workspaceId,
      sourceId: id,
      error: sourceResult.error,
    });
    return (
      <p
        role="alert"
        className="text-ink"
        style={{ font: "var(--font-title-md)" }}
      >
        {SOURCE_LOAD_ERROR_HEADING}
      </p>
    );
  }

  if (!sourceResult.data) {
    return (
      <p className="text-ink" style={{ font: "var(--font-title-md)" }}>
        {SOURCE_NOT_FOUND_HEADING}
      </p>
    );
  }

  if (chunksResult.error || wikiResult.error) {
    console.error("소스 상세 관련 데이터 조회 실패", {
      workspaceId,
      sourceId: id,
      chunksError: chunksResult.error,
      wikiError: wikiResult.error,
    });
    return (
      <p
        role="alert"
        className="text-ink"
        style={{ font: "var(--font-title-md)" }}
      >
        {SOURCE_LOAD_ERROR_HEADING}
      </p>
    );
  }

  const source = sourceResult.data;
  const chunks = chunksResult.data ?? [];
  const isOwner = memberResult?.data?.role === "owner";

  const citingPages = (wikiResult.data ?? [])
    .filter((page) => {
      if (!Array.isArray(page.sources)) return false;
      return page.sources.some((entry) => {
        const rawSourceId =
          typeof entry === "string"
            ? entry
            : ((entry as { raw_source_id?: string })?.raw_source_id ?? null);
        return rawSourceId === id;
      });
    })
    .map((page) => ({
      id: page.id,
      title: page.title,
      slug: page.slug,
      category: page.category,
    }));

  return (
    <SourceDetailContent
      workspaceId={workspaceId}
      source={source}
      chunks={chunks}
      citingPages={citingPages}
      isOwner={isOwner}
    />
  );
}

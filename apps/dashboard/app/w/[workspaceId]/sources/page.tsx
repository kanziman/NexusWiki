import { SourcesList } from "@/components/SourcesList";
import { createClient } from "@/lib/supabase/server";

type SourcesPageProps = {
  params: Promise<{ workspaceId: string }>;
  searchParams: Promise<{ prefillTitle?: string; tab?: string }>;
};

// UI-03 소스 목록 라우트. 이 파일 자신은 Server Component로 남아 요청자
// 세션으로 초기 목록만 읽는다(RLS raw_sources_select_member) — 실제 상호작용
// (Dropzone 제출, JobStepper 폴링, 로컬 state에 새 소스 prepend)은
// SourcesList.tsx(클라이언트 컴포넌트)에 위임한다.
//
// content는 select하지 않는다 — 목록 화면은 메타데이터만 필요하고, 잠재적으로
// 큰 추출 텍스트 컬럼을 브라우저로 내려보내지 않는다(threat_model T-06-15).
//
// prefillTitle/tab은 RedLinkCta.handleCreate가 심는 쿼리 파라미터 —
// 06-REVIEW.md CR-01: 이전에는 여기서 읽지 않아 SourcesList/Dropzone까지
// 전달되지 않았다.
export default async function SourcesPage({
  params,
  searchParams,
}: SourcesPageProps) {
  const { workspaceId } = await params;
  const { prefillTitle, tab } = await searchParams;
  const supabase = await createClient();

  const { data } = await supabase
    .from("raw_sources")
    .select("id,title,source_type,created_at,content_hash")
    .eq("workspace_id", workspaceId)
    .order("created_at", { ascending: false })
    .limit(50);

  return (
    <SourcesList
      workspaceId={workspaceId}
      initialSources={data ?? []}
      prefillTitle={prefillTitle}
      initialTab={tab === "text" ? "text" : undefined}
    />
  );
}

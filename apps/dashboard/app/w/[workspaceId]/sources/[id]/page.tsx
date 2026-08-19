import { DetailHeader, StatusBadge } from "@/components/DashboardPrimitives";
import { workspacePath } from "@/lib/workspace-path";
import { createClient } from "@/lib/supabase/server";

type SourceDetailRouteProps = {
  params: Promise<{ workspaceId: string; id: string }>;
};

const SOURCE_NOT_FOUND_HEADING = "자료를 찾을 수 없습니다";

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("ko-KR", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

/**
 * 자료 상세 라우트 — wiki/[slug]/page.tsx와 같은 패턴(Server Component,
 * workspace_id로 스코프된 단일 행 조회, RLS 실패는 고정 not-found 문구).
 *
 * 관련: openspec/changes/archive/2026-08-14-complete-library-selection-layout
 * (library-selection-layout 스펙 — WikiLibrary가 이미 쓰는 "행 → 실제 라우트"
 * 패턴을 Sources 쪽에도 맞춘다).
 * 설계 근거: supabase/migrations/0004_rls_policies.sql 섹션 5
 *            (raw_sources_select_member)
 */
export default async function SourceDetailRoute({
  params,
}: SourceDetailRouteProps) {
  const { workspaceId, id } = await params;

  const supabase = await createClient();

  const { data: source, error } = await supabase
    .from("raw_sources")
    .select("id,title,source_type,created_at")
    .eq("workspace_id", workspaceId)
    .eq("id", id)
    .single();

  if (error || !source) {
    return (
      <p className="text-ink" style={{ font: "var(--font-title-md)" }}>
        {SOURCE_NOT_FOUND_HEADING}
      </p>
    );
  }

  return (
    <div className="mx-auto flex w-full max-w-4xl flex-col gap-xl">
      <DetailHeader
        libraryHref={`${workspacePath(workspaceId)}/sources`}
        libraryLabel="자료 목록"
        kind={source.source_type}
        title={source.title}
        meta={<StatusBadge>{formatDate(source.created_at)}</StatusBadge>}
      />
      <dl className="grid gap-sm text-sm sm:grid-cols-2">
        <div>
          <dt className="text-[var(--muted)]">유형</dt>
          <dd className="mt-xs text-[var(--fg)]">{source.source_type}</dd>
        </div>
        <div>
          <dt className="text-[var(--muted)]">등록일</dt>
          <dd className="mt-xs text-[var(--fg)]">
            {formatDate(source.created_at)}
          </dd>
        </div>
      </dl>
    </div>
  );
}

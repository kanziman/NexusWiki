import { SourcesList, type SourceRow } from "@/components/SourcesList";
import { createClient } from "@/lib/supabase/server";

type SourcesPageProps = {
  params: Promise<{ workspaceId: string }>;
  searchParams: Promise<{ prefillTitle?: string; tab?: string }>;
};

const PAGE_SIZE = 50;

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
    .select("id,title,source_type,mime_type,byte_size,created_at,content_hash")
    .eq("workspace_id", workspaceId)
    .order("created_at", { ascending: false })
    .limit(PAGE_SIZE);

  const sources = (data ?? []) as SourceRow[];
  const sourceIds = sources.map((source) => source.id);

  // PRD §3.3 "청크 및 좌표" · "연결된 위키 문서" 두 열의 데이터.
  //
  // ⚠️ 소스마다 따로 조회하면 목록 한 번에 N+1 쿼리가 된다. 대신 화면에
  // 보이는 소스 id 집합으로 한 번씩만 읽고 여기서 집계한다. PRD §4.1 이
  // 요구하는 역인용 인덱스는 아직 없으므로(마이그레이션 미적용) 위키 쪽도
  // 워크스페이스 단위로 한 번 읽어 JS 에서 매핑한다 — 인덱스가 생기면
  // 이 두 조회는 RPC 하나로 접을 수 있다.
  let user = null;
  if (supabase.auth?.getUser) {
    const { data } = await supabase.auth.getUser();
    user = data?.user ?? null;
  }

  const [chunkResult, wikiResult, memberResult] = await Promise.all([
    sourceIds.length
      ? supabase
          .from("source_chunks")
          .select("raw_source_id,char_start,char_end")
          .eq("workspace_id", workspaceId)
          .in("raw_source_id", sourceIds)
      : Promise.resolve({ data: [] }),
    supabase
      .from("wiki_pages")
      .select("id,title,slug,sources")
      .eq("workspace_id", workspaceId),
    user
      ? supabase
          .from("workspace_members")
          .select("role")
          .eq("workspace_id", workspaceId)
          .eq("user_id", user.id)
          .maybeSingle()
      : Promise.resolve({ data: null }),
  ]);

  const isOwner = memberResult?.data?.role === "owner";

  // ⚠️ 아래 두 집계는 실패해도 `?? []`로 흘러가 빈 결과와 구분되지 않는다.
  // 목록 요약이 "고아 소스 없음"·"전 소스 청킹 완료" 같은 단정을 하므로, 조회
  // 실패를 그대로 두면 화면이 거짓을 확언한다. 소스 상세 라우트가 이미
  // `sources/[id]/page.tsx`에서 같은 분기를 하고 있다 — 목록도 실패 사실을
  // 내려보내 해당 칸이 단정 대신 집계 불가를 말하게 한다.
  const chunkStatsUnavailable = Boolean(
    (chunkResult as { error?: unknown } | null)?.error,
  );
  const citingPagesUnavailable = Boolean(wikiResult.error);

  if (chunkStatsUnavailable || citingPagesUnavailable) {
    console.error("소스 목록 집계 조회 실패", {
      workspaceId,
      chunkError: (chunkResult as { error?: unknown } | null)?.error,
      wikiError: wikiResult.error,
    });
  }

  const chunkStats = new Map<
    string,
    { count: number; charStart: number; charEnd: number }
  >();
  for (const chunk of chunkResult.data ?? []) {
    const previous = chunkStats.get(chunk.raw_source_id);
    if (!previous) {
      chunkStats.set(chunk.raw_source_id, {
        count: 1,
        charStart: chunk.char_start,
        charEnd: chunk.char_end,
      });
      continue;
    }
    previous.count += 1;
    previous.charStart = Math.min(previous.charStart, chunk.char_start);
    previous.charEnd = Math.max(previous.charEnd, chunk.char_end);
  }

  const citingPages = new Map<string, { title: string; slug: string }[]>();
  for (const page of wikiResult.data ?? []) {
    if (!Array.isArray(page.sources)) continue;
    for (const entry of page.sources) {
      // sources 항목의 모양은 컴파일러가 소유한다 — 문자열 id 일 수도,
      // {raw_source_id} 를 품은 객체일 수도 있다. 둘 다 받아준다.
      const rawSourceId =
        typeof entry === "string"
          ? entry
          : ((entry as { raw_source_id?: string })?.raw_source_id ?? null);
      if (!rawSourceId) continue;
      const list = citingPages.get(rawSourceId) ?? [];
      list.push({ title: page.title, slug: page.slug });
      citingPages.set(rawSourceId, list);
    }
  }

  return (
    <SourcesList
      workspaceId={workspaceId}
      initialSources={sources}
      chunkStats={Object.fromEntries(chunkStats)}
      citingPages={Object.fromEntries(citingPages)}
      chunkStatsUnavailable={chunkStatsUnavailable}
      citingPagesUnavailable={citingPagesUnavailable}
      prefillTitle={prefillTitle}
      initialTab={tab === "text" ? "text" : undefined}
      isOwner={isOwner}
    />
  );
}

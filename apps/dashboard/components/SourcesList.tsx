"use client";

import * as Dialog from "@radix-ui/react-dialog";
import {
  Activity,
  AlertTriangle,
  FileText,
  Layers,
  Link2,
  Loader2,
  Plus,
  Search,
  Sparkles,
  Trash2,
  X,
} from "lucide-react";
import Link from "next/link";
import React, { useEffect, useState } from "react";

import { Dropzone } from "@/components/Dropzone";
import { JobStepper } from "@/components/JobStepper";
import { Pagination } from "@/components/Pagination";
import { ApiError, apiFetch } from "@/lib/api-client";
import { formatDate, formatRelativeTime } from "@/lib/relative-time";
import { createClient } from "@/lib/supabase/client";
import { workspacePath } from "@/lib/workspace-path";

export type SourceRow = {
  id: string;
  title: string;
  source_type: string;
  mime_type?: string | null;
  byte_size?: number | null;
  created_at: string;
  content_hash: string;
};

export type ChunkStat = { count: number; charStart: number; charEnd: number };
export type CitingPage = { title: string; slug: string };

export type SourcesListProps = {
  workspaceId: string;
  initialSources: SourceRow[];
  chunkStats?: Record<string, ChunkStat>;
  citingPages?: Record<string, CitingPage[]>;
  // 집계 조회가 실패했는지. 빈 결과와 구분하지 못하면 요약이 "고아 소스 없음"
  // 같은 단정을 사실인 것처럼 표시한다.
  chunkStatsUnavailable?: boolean;
  citingPagesUnavailable?: boolean;
  prefillTitle?: string;
  initialTab?: "text";
  isOwner?: boolean;
};

const EMPTY_HEADING = "아직 등록된 소스가 없습니다";
const EMPTY_BODY =
  "파일을 드래그하거나 URL/텍스트를 붙여넣어 첫 소스를 추가하세요.";

// 집계 조회가 실패했을 때의 문구. 빈 결과인 척 0을 보여주거나 "고아 소스 없음"
// 같은 단정을 하면 화면이 모르는 것을 아는 것처럼 말하게 된다.
const AGGREGATE_UNAVAILABLE = "집계를 불러오지 못했습니다";

const SELECT_COLUMNS =
  "id,title,source_type,mime_type,byte_size,created_at,content_hash";

function formatBytes(bytes?: number | null): string | null {
  if (bytes === null || bytes === undefined) return null;
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

type MimeFilter = "all" | "pdf" | "text_md";

function isPdf(source: SourceRow): boolean {
  return (
    source.mime_type === "application/pdf" ||
    source.title.toLowerCase().endsWith(".pdf")
  );
}

function isTextMd(source: SourceRow): boolean {
  return (
    source.mime_type === "text/plain" ||
    source.mime_type === "text/markdown" ||
    ["text", "clipping", "article"].includes(source.source_type) ||
    source.title.toLowerCase().endsWith(".md") ||
    source.title.toLowerCase().endsWith(".txt")
  );
}

function formatLabel(source: SourceRow): { label: string; variant: string } {
  if (isPdf(source)) return { label: "PDF", variant: "pdf" };
  if (source.mime_type === "text/markdown" || source.title.endsWith(".md")) {
    return { label: "MD", variant: "md" };
  }
  return { label: "TXT", variant: "txt" };
}

export function SourcesList({
  workspaceId,
  initialSources,
  chunkStats = {},
  citingPages = {},
  chunkStatsUnavailable = false,
  citingPagesUnavailable = false,
  prefillTitle,
  initialTab,
  isOwner = false,
}: SourcesListProps) {
  const [sources, setSources] = useState<SourceRow[]>(initialSources);
  const [activeMime, setActiveMime] = useState<MimeFilter>("all");
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);
  const [uploadOpen, setUploadOpen] = useState(
    Boolean(prefillTitle) || initialTab === "text",
  );

  const [sourceToDelete, setSourceToDelete] = useState<SourceRow | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<{
    type: "success" | "error";
    text: string;
  } | null>(null);

  const PAGE_SIZE = 8;

  useEffect(() => {
    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search);
      if (params.get("deleted") === "true") {
        setFeedback({
          type: "success",
          text: "원본 소스가 영구 삭제되었습니다.",
        });
        const url = new URL(window.location.href);
        url.searchParams.delete("deleted");
        window.history.replaceState(
          null,
          "",
          url.pathname + (url.search ? url.search : ""),
        );
      }
    }
  }, []);

  async function handleIngested(_jobId: string, rawSourceId: string) {
    const supabase = createClient();
    const { data } = await supabase
      .from("raw_sources")
      .select(SELECT_COLUMNS)
      .eq("id", rawSourceId)
      .single<SourceRow>();

    if (data) {
      setSources((prev) => [data, ...prev]);
      setUploadOpen(false);
    }
  }

  async function handleDeleteSource(target: SourceRow) {
    if (!isOwner || deletingId) return;
    setDeletingId(target.id);
    setDeleteError(null);
    try {
      await apiFetch(`/workspaces/${workspaceId}/sources/${target.id}`, {
        method: "DELETE",
      });
      setSources((prev) => {
        const next = prev.filter((s) => s.id !== target.id);
        const nextSearched = query.trim()
          ? next.filter((s) =>
              s.title.toLowerCase().includes(query.trim().toLowerCase()),
            )
          : next;
        const nextFiltered = nextSearched.filter((s) => {
          if (activeMime === "all") return true;
          if (activeMime === "pdf") return isPdf(s);
          return isTextMd(s);
        });
        const maxPage = Math.max(1, Math.ceil(nextFiltered.length / PAGE_SIZE));
        setPage((curr) => Math.min(curr, maxPage));
        return next;
      });
      setDeletingId(null);
      setSourceToDelete(null);
      setFeedback({
        type: "success",
        text: `'${target.title}' 원본 소스가 영구 삭제되었습니다.`,
      });
    } catch (err: unknown) {
      setDeletingId(null);
      setDeleteError(
        err instanceof ApiError && err.detail === "source_in_use"
          ? "이 원문을 참조하는 위키·공개본·대화 또는 진행 중 작업이 있습니다. 관련 항목을 먼저 정리해주세요."
          : "소스를 삭제하지 못했습니다. 다시 시도해주세요.",
      );
    }
  }

  const searched = query.trim()
    ? sources.filter((source) =>
        source.title.toLowerCase().includes(query.trim().toLowerCase()),
      )
    : sources;

  const filteredSources = searched.filter((source) => {
    if (activeMime === "all") return true;
    if (activeMime === "pdf") return isPdf(source);
    return isTextMd(source);
  });

  const paginatedSources = filteredSources.slice(
    (page - 1) * PAGE_SIZE,
    page * PAGE_SIZE,
  );

  const pdfCount = sources.filter(isPdf).length;
  const textMdCount = sources.filter(isTextMd).length;
  // ⚠️ Object.values(chunkStats) 전량을 합치면 안 된다. chunkStats 는 서버
  // props 라 삭제된 소스의 항목이 그대로 남아 있어, 행은 사라졌는데 청크
  // 합계만 그 소스분을 계속 포함하는 모순이 생긴다. 요약은 항상 지금 그리는
  // sources 에서 파생시킨다.
  const totalChunks = sources.reduce(
    (sum, source) => sum + (chunkStats[source.id]?.count ?? 0),
    0,
  );
  const indexedCount = sources.filter(
    (source) => (chunkStats[source.id]?.count ?? 0) > 0,
  ).length;

  // 벤토 네 지표는 전부 이미 내려온 props에서 나온다 — 새 조회를 만들지 않는다.
  //
  // ⚠️ chunkStats·citingPages 는 서버 props 라 업로드 직후 새 소스에는 값이
  // 없다. 이때 분모만 늘고 분자는 그대로여서 연결률이 잠깐 내려가는데, 이는
  // 실제 상태다(방금 올린 소스는 아직 청킹·인용 전이다) — 보정하지 않는다.
  const citedCount = sources.filter(
    (source) => (citingPages[source.id]?.length ?? 0) > 0,
  ).length;
  const orphanCount = sources.length - citedCount;
  const pendingChunkCount = sources.length - indexedCount;
  const citationRate =
    sources.length === 0 ? 0 : Math.round((citedCount / sources.length) * 100);
  const indexingRate =
    sources.length === 0
      ? 0
      : Math.round((indexedCount / sources.length) * 100);

  const TABS: { id: MimeFilter; label: string }[] = [
    { id: "all", label: `전체 ${sources.length}` },
    { id: "pdf", label: `PDF ${pdfCount}` },
    { id: "text_md", label: `텍스트/마크다운 ${textMdCount}` },
  ];

  return (
    <div className="content sources">
      {/* 헤더 영역 */}
      <section className="hero" data-od-id="source-management-header">
        <div>
          <h1>원문 소스 관리</h1>
          <p>
            등록된 원본의 청킹, 5채널 인덱싱 상태와 위키 인용 관계를 관리합니다.
          </p>
        </div>
        {sources.length > 0 && (
          <button
            type="button"
            className="button primary inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg shadow-xs"
            onClick={() => setUploadOpen(true)}
            data-od-id="upload-open"
          >
            <Plus size={14} aria-hidden="true" />
            <span>소스 업로드</span>
          </button>
        )}
      </section>

      {/* 파이프라인 요약 벤토 (소스가 있을 때만 표시).
          네 칸 모두 수치와 라벨을 텍스트로 함께 둔다 — 색만으로 상태를
          전달하면 색을 구분하지 못하는 사용자에게 지표가 사라진다. */}
      {sources.length > 0 && (
        <section
          className="mt-8 mb-2 grid grid-cols-2 gap-3.5 md:grid-cols-4"
          aria-label="파이프라인 요약"
          data-od-id="pipeline-stats"
        >
          {/* 1. 총 등록 원문 */}
          <div className="flex flex-col gap-2.5 overflow-hidden rounded-[14px] border border-[var(--border)] bg-[var(--surface)] px-[18px] py-4">
            <div className="flex items-center justify-between text-[12px] font-semibold text-[var(--muted)]">
              <span>총 등록 원문</span>
              <FileText size={16} aria-hidden="true" />
            </div>
            <div className="flex flex-wrap items-baseline gap-2">
              <b className="font-mono text-[26px] font-extrabold tracking-tight text-[var(--fg)]">
                {sources.length}
              </b>
              <span className="text-[11px] text-[var(--muted)]">개 문서</span>
            </div>
            <div className="flex flex-wrap items-center gap-1.5 text-[11px] font-bold">
              <span className="rounded-md bg-[var(--soft)] px-1.5 py-0.5 text-[var(--accent)]">
                {`텍스트·마크다운 ${textMdCount}`}
              </span>
              <span className="rounded-md bg-[var(--border)]/50 px-1.5 py-0.5 text-[var(--muted)]">
                {`PDF ${pdfCount}`}
              </span>
            </div>
          </div>

          {/* 2. 생성된 청크 */}
          <div className="flex flex-col gap-2.5 overflow-hidden rounded-[14px] border border-[var(--border)] bg-[var(--surface)] px-[18px] py-4">
            <div className="flex items-center justify-between text-[12px] font-semibold text-[var(--muted)]">
              <span>생성된 청크</span>
              <Layers size={16} aria-hidden="true" />
            </div>
            {chunkStatsUnavailable ? (
              <span className="text-[12px] font-semibold text-[var(--muted)]">
                {AGGREGATE_UNAVAILABLE}
              </span>
            ) : (
              <>
                <div className="flex flex-wrap items-baseline gap-2">
                  <b className="font-mono text-[26px] font-extrabold tracking-tight text-[var(--fg)]">
                    {totalChunks}
                  </b>
                  <span className="text-[11px] text-[var(--muted)]">청크</span>
                </div>
                <span className="text-[11px] text-[var(--muted)]">
                  {`${indexedCount}/${sources.length} 소스 청킹 완료`}
                </span>
              </>
            )}
          </div>

          {/* 3. 위키 인용 연결률 */}
          <div className="flex flex-col gap-2.5 overflow-hidden rounded-[14px] border border-[var(--border)] bg-[var(--surface)] px-[18px] py-4">
            <div className="flex items-center justify-between text-[12px] font-semibold text-[var(--muted)]">
              <span>위키 인용 연결률</span>
              <Link2 size={16} aria-hidden="true" />
            </div>
            {citingPagesUnavailable ? (
              <span className="text-[12px] font-semibold text-[var(--muted)]">
                {AGGREGATE_UNAVAILABLE}
              </span>
            ) : (
              <>
                <div className="flex flex-wrap items-baseline gap-2">
                  <b className="font-mono text-[26px] font-extrabold tracking-tight text-[var(--fg)]">
                    {`${citedCount}/${sources.length}`}
                  </b>
                  <span className="text-[11px] text-[var(--muted)]">
                    {`인용됨 (${citationRate}%)`}
                  </span>
                </div>
                <span className="text-[11px] text-[var(--muted)]">
                  {orphanCount === 0
                    ? "고아 소스 없음"
                    : `아직 인용되지 않은 소스 ${orphanCount}개`}
                </span>
              </>
            )}
          </div>

          {/* 4. 파이프라인 상태 — 워크스페이스 단위 5단계 집계는 jobs 를 새로
              읽어야 하므로, 이미 있는 신호인 청킹 완료율로 정의한다. 행 단위
              5단계 진행은 아래 목록의 JobStepper 가 계속 담당한다. */}
          <div className="flex flex-col gap-2.5 overflow-hidden rounded-[14px] border border-[var(--border)] bg-[var(--surface)] px-[18px] py-4">
            <div className="flex items-center justify-between text-[12px] font-semibold text-[var(--muted)]">
              <span>파이프라인 상태</span>
              <Activity
                size={16}
                className={
                  !chunkStatsUnavailable && pendingChunkCount === 0
                    ? "text-[var(--good)]"
                    : "text-[var(--muted)]"
                }
                aria-hidden="true"
              />
            </div>
            {chunkStatsUnavailable ? (
              <span className="text-[12px] font-semibold text-[var(--muted)]">
                {AGGREGATE_UNAVAILABLE}
              </span>
            ) : (
              <>
                <div className="flex flex-wrap items-baseline gap-2">
                  <b className="font-mono text-[26px] font-extrabold tracking-tight text-[var(--fg)]">
                    {`${indexingRate}%`}
                  </b>
                  <span
                    className={`rounded-md px-1.5 py-0.5 text-[11px] font-bold ${
                      pendingChunkCount === 0
                        ? "bg-[var(--good)]/12 text-[var(--good)]"
                        : "bg-[var(--border)]/50 text-[var(--muted)]"
                    }`}
                  >
                    {pendingChunkCount === 0
                      ? "전 소스 청킹 완료"
                      : "청킹 진행 중"}
                  </span>
                </div>
                <span className="text-[11px] text-[var(--muted)]">
                  {pendingChunkCount === 0
                    ? "청킹 대기 중인 소스 없음"
                    : `청킹 대기 ${pendingChunkCount}개`}
                </span>
              </>
            )}
          </div>
        </section>
      )}

      {/* 피드백 메시지 알림 */}
      {feedback && (
        <div
          role="status"
          className={`flex items-center justify-between gap-2 p-3 my-3 rounded-lg text-xs font-medium border ${
            feedback.type === "success"
              ? "bg-[var(--good-soft)] border-[var(--good)]/30 text-[var(--good)]"
              : "bg-[var(--danger-soft)] border-[var(--danger)]/30 text-[var(--danger)]"
          }`}
        >
          <span>{feedback.text}</span>
          <button
            type="button"
            onClick={() => setFeedback(null)}
            className="p-1 hover:opacity-80 transition-opacity cursor-pointer"
            aria-label="알림 닫기"
          >
            <X size={13} />
          </button>
        </div>
      )}

      {/* 툴바 & 테이블 섹션 */}
      <section data-od-id="source-table-section">
        {sources.length > 0 && (
          <div className="toolbar flex items-center justify-between gap-4">
            {/* ⚠️ 공용 .tabs/.tab 클래스를 쓰지 않는다. .content.sources .tab 은
                밑줄 탭(padding 8px 10px, border-bottom)이라 높이가 컨텐츠에
                따라 흔들리고, 옆의 .field.search(36px 고정)와 수평선이
                어긋난다. 세그먼트 칩은 h-9(36px)로 직접 못박는다.
                필터는 상호배타적 단일 선택이므로 tab 시맨틱을 유지한다. */}
            <nav
              className="flex h-9 flex-wrap items-center gap-1"
              role="tablist"
              aria-label="파일 형식 필터"
            >
              {TABS.map((tab) => (
                <button
                  key={tab.id}
                  type="button"
                  role="tab"
                  aria-selected={activeMime === tab.id}
                  onClick={() => {
                    setActiveMime(tab.id);
                    setPage(1);
                  }}
                  className={`nw-focus-ring box-border inline-flex h-9 cursor-pointer items-center rounded-lg border px-3 text-[12px] font-bold transition-colors ${
                    activeMime === tab.id
                      ? "border-[var(--accent)] bg-[var(--soft)] text-[var(--accent)]"
                      : "border-[var(--border)] bg-[var(--surface)] text-[var(--muted)] hover:border-[var(--border-strong)] hover:text-[var(--fg)]"
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </nav>

            {/* 검색창. .field.search 가 높이 36px 를 고정한다 — 이 규칙은 위키
                라이브러리 검색창과 공유하므로 여기서 고치지 않는다. */}
            <div className="relative h-9 w-full max-w-[360px] flex-none">
              <Search
                size={14}
                className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--muted)] pointer-events-none"
              />
              <input
                className="field search"
                value={query}
                onChange={(event) => {
                  setQuery(event.target.value);
                  setPage(1);
                }}
                placeholder="파일명으로 검색"
                aria-label="파일명으로 검색"
              />
            </div>
          </div>
        )}

        {sources.length === 0 ? (
          <div
            className="empty-sources-canvas w-full rounded-2xl border border-[var(--border)] bg-[var(--bg)] p-6 md:p-10 mt-4 shadow-xs"
            data-testid="empty-sources-dropzone-container"
          >
            {/* max-w-lg는 쓰지 않는다 — --spacing-lg(24px) 간격 토큰과 이름이 충돌해
                Tailwind가 컨테이너 스케일(32rem) 대신 24px를 max-width로 먹인다.
                tests/PublicLandingPage.test.tsx의 max-w-xl 회귀 테스트와 같은 종류의 함정. */}
            <div className="text-center max-w-[32rem] mx-auto mb-8">
              <div className="inline-flex h-10 w-10 items-center justify-center rounded-xl bg-[var(--soft)] text-[var(--accent)] mb-3 shadow-2xs">
                <Sparkles size={20} aria-hidden="true" />
              </div>
              <h2 className="text-base md:text-lg font-bold text-[var(--fg)] tracking-tight break-keep">
                {EMPTY_HEADING}
              </h2>
              <p className="mt-1.5 text-xs md:text-sm text-[var(--muted)] leading-relaxed break-keep">
                {EMPTY_BODY}
              </p>
            </div>
            <div className="w-full max-w-3xl mx-auto">
              <Dropzone
                workspaceId={workspaceId}
                onIngested={handleIngested}
                prefillTitle={prefillTitle}
                initialTab={initialTab}
              />
            </div>
          </div>
        ) : filteredSources.length === 0 ? (
          <div className="table-wrap p-12 text-center border border-[var(--border)] rounded-lg bg-[var(--surface)]/30 mt-3">
            <b className="block text-[14px] text-[var(--fg)]">
              해당 조건의 소스가 없습니다
            </b>
            <span className="mt-1.5 block text-xs text-[var(--muted)]">
              다른 형식 탭을 선택하거나 검색어를 지우세요.
            </span>
          </div>
        ) : (
          /* 일체형 목록 컨테이너.
             ⚠️ 컬럼 정의는 --sources-cols 한 곳에만 쓴다. 헤더 행과 데이터 행이
             각자 폭을 선언하면 한쪽만 고쳤을 때 축이 어긋난다(계획서 §3.2 가
             지적한 '작업' 헤더와 삭제 아이콘의 어긋남이 바로 그 증상이다).
             md 미만에서는 컬럼을 풀어 세로로 쌓는다 — 5열을 좁은 화면에
             밀어 넣으면 페이지 가로 스크롤이 강제된다. */
          <div
            className="mt-3 overflow-hidden rounded-xl border border-[var(--border)] bg-[var(--bg)]"
            id="sources-library"
            style={
              {
                "--sources-cols":
                  "minmax(0,26fr) minmax(0,24fr) minmax(0,14fr) minmax(0,20fr) minmax(0,16fr)",
              } as React.CSSProperties
            }
          >
            {/* 컬럼 헤더 — 좁은 화면에서는 행이 세로로 쌓이므로 감춘다 */}
            <div
              className="hidden items-center gap-4 border-b border-[var(--border)] bg-[var(--surface)] px-4 py-2.5 text-[11px] font-bold tracking-wider text-[var(--muted)] uppercase md:grid"
              style={{ gridTemplateColumns: "var(--sources-cols)" }}
            >
              <span>소스 파일</span>
              <span>연결된 위키 문서</span>
              <span className="text-right">청크 및 좌표</span>
              <span>파이프라인</span>
              <span className="text-right">작업</span>
            </div>

            <div className="divide-y divide-[var(--border)]">
              {paginatedSources.map((source) => {
                const format = formatLabel(source);
                const size = formatBytes(source.byte_size);
                const stat = chunkStats[source.id];
                const cited = citingPages[source.id] ?? [];
                // 인용 수에 따라 행이 세로로 늘어나는 것이 목록 리듬이 깨지는
                // 직접 원인이다. 두 개만 그리고 나머지는 개수로 접는다 —
                // 전체 인용 목록은 소스 상세에서 볼 수 있다.
                const visibleCited = cited.slice(0, 2);
                const hiddenCitedCount = cited.length - visibleCited.length;

                return (
                  <article
                    key={source.id}
                    className="grid grid-cols-1 items-center gap-3 px-4 py-3 transition-colors hover:bg-[var(--surface)]/40 md:h-[72px] md:gap-4 md:py-0 md:[grid-template-columns:var(--sources-cols)]"
                  >
                    {/* 1. 소스 파일 */}
                    <div className="flex min-w-0 items-center gap-2.5">
                      <span className={`format ${format.variant}`}>
                        {format.label}
                      </span>
                      <div className="min-w-0 flex-1">
                        <Link
                          href={`${workspacePath(workspaceId)}/sources/${source.id}`}
                          className="group block truncate"
                        >
                          <b
                            title={source.title}
                            aria-label={source.title}
                            className="block truncate text-[13px] font-bold text-[var(--fg)] transition-colors group-hover:text-[var(--accent)] group-hover:underline"
                          >
                            {source.title}
                          </b>
                        </Link>
                        {/* 업로드 열을 없애지 않고 여기로 접었다. 절대 일자를
                            빼면 정확한 출처 시점을 행에서 되짚을 수 없다. */}
                        <div className="mt-0.5 flex min-w-0 items-center gap-1 truncate text-[11px] text-[var(--muted)]">
                          {size && (
                            <>
                              <span>{size}</span>
                              <span aria-hidden="true">·</span>
                            </>
                          )}
                          <span>{source.source_type}</span>
                          <span aria-hidden="true">·</span>
                          <span>{formatRelativeTime(source.created_at)}</span>
                          <span aria-hidden="true">·</span>
                          <span>{formatDate(source.created_at)}</span>
                        </div>
                      </div>
                    </div>

                    {/* 2. 연결된 위키 문서 */}
                    <div className="min-w-0">
                      {citingPagesUnavailable ? (
                        <span className="text-[11px] text-[var(--muted)] italic">
                          인용 정보를 불러오지 못했습니다
                        </span>
                      ) : cited.length === 0 ? (
                        <span className="text-[11px] text-[var(--muted)] italic">
                          인용한 위키 없음
                        </span>
                      ) : (
                        <div className="flex min-w-0 items-center gap-1.5 overflow-hidden whitespace-nowrap">
                          {visibleCited.map((page) => (
                            <Link
                              key={page.slug}
                              href={`${workspacePath(workspaceId)}/wiki/${page.slug}`}
                              className="doc-chip min-w-0"
                              title={page.title}
                            >
                              <span className="truncate">{page.title}</span>
                            </Link>
                          ))}
                          {hiddenCitedCount > 0 && (
                            <span className="flex-none text-[11px] font-semibold text-[var(--muted)]">
                              {`+${hiddenCitedCount}개 더`}
                            </span>
                          )}
                        </div>
                      )}
                    </div>

                    {/* 3. 청크 및 좌표 */}
                    <div className="whitespace-nowrap md:text-right">
                      {chunkStatsUnavailable ? (
                        <span className="text-[11px] text-[var(--muted)]">
                          집계 불가
                        </span>
                      ) : stat ? (
                        <>
                          <b className="block text-[12.5px] font-bold text-[var(--fg)]">
                            {stat.count} 청크
                          </b>
                          <span className="mt-0.5 block font-mono text-[10.5px] text-[var(--muted)]">
                            {stat.charStart.toLocaleString("ko-KR")}–
                            {stat.charEnd.toLocaleString("ko-KR")} char
                          </span>
                        </>
                      ) : (
                        <span className="text-[11px] text-[var(--muted)]">
                          청크 없음
                        </span>
                      )}
                    </div>

                    {/* 4. 파이프라인 — 행 단위 5단계 진행은 계속 JobStepper 가
                        담당한다. 벤토의 요약 지표는 청킹 완료율일 뿐이다. */}
                    <div className="min-w-0">
                      <JobStepper
                        workspaceId={workspaceId}
                        rawSourceId={source.id}
                      />
                    </div>

                    {/* 5. 작업 (상세 보기 & 삭제) */}
                    <div className="flex items-center gap-2 whitespace-nowrap md:justify-end">
                      <Link
                        href={`${workspacePath(workspaceId)}/sources/${source.id}`}
                        className="text-button inline-flex items-center gap-0.5 text-xs font-semibold text-[var(--accent)] hover:underline"
                      >
                        <span>상세 보기</span>
                      </Link>
                      {isOwner && (
                        <button
                          type="button"
                          onClick={() => {
                            setDeleteError(null);
                            setSourceToDelete(source);
                          }}
                          className="nw-focus-ring inline-flex w-[30px] flex-none cursor-pointer items-center justify-center rounded p-1 text-[var(--muted)] transition-colors hover:bg-[var(--danger-soft)] hover:text-[var(--danger)]"
                          title="원문 소스 삭제"
                          data-testid={`delete-source-btn-${source.id}`}
                        >
                          <Trash2 size={13} aria-hidden="true" />
                          <span className="sr-only">삭제</span>
                        </button>
                      )}
                    </div>
                  </article>
                );
              })}
            </div>
          </div>
        )}

        {filteredSources.length > 0 && (
          <Pagination
            currentPage={page}
            totalItems={filteredSources.length}
            pageSize={PAGE_SIZE}
            onPageChange={setPage}
          />
        )}
      </section>

      {/* 업로드 모달 */}
      <Dialog.Root open={uploadOpen} onOpenChange={setUploadOpen}>
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 z-50 bg-black/60 backdrop-blur-md transition-all duration-200 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0" />
          <Dialog.Content className="fixed top-1/2 left-1/2 z-50 w-[min(720px,calc(100vw-32px))] max-h-[90vh] -translate-x-1/2 -translate-y-1/2 overflow-y-auto rounded-2xl border border-[var(--border)] bg-[var(--bg)] p-6 md:p-8 shadow-2xl outline-none duration-200 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95">
            <div className="modal-head mb-6 flex items-start justify-between gap-4">
              <div>
                <Dialog.Title className="text-lg md:text-xl font-bold text-[var(--fg)] tracking-tight">
                  소스 업로드
                </Dialog.Title>
                <p className="mt-1.5 text-xs md:text-sm text-[var(--muted)]">
                  파일, 웹 URL 또는 텍스트를 등록하여 위키 지식 베이스를
                  확장합니다.
                </p>
              </div>
              <Dialog.Close asChild>
                <button
                  type="button"
                  className="icon-btn rounded-xl p-1.5 text-[var(--muted)] hover:bg-[var(--surface)] hover:text-[var(--fg)] transition-colors cursor-pointer"
                  aria-label="닫기"
                >
                  <X size={20} aria-hidden="true" />
                </button>
              </Dialog.Close>
            </div>
            <Dropzone
              workspaceId={workspaceId}
              onIngested={handleIngested}
              prefillTitle={prefillTitle}
              initialTab={initialTab}
            />
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>

      {/* 소스 삭제 확인 모달 */}
      <Dialog.Root
        open={Boolean(sourceToDelete)}
        onOpenChange={(open) => {
          if (!open) {
            setSourceToDelete(null);
            setDeleteError(null);
          }
        }}
      >
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 z-50 bg-black/60 backdrop-blur-md transition-all duration-200" />
          <Dialog.Content className="fixed top-1/2 left-1/2 z-50 w-[min(480px,calc(100vw-32px))] -translate-x-1/2 -translate-y-1/2 rounded-2xl border border-[var(--border)] bg-[var(--bg)] p-6 shadow-2xl outline-none">
            <div className="modal-head mb-4 flex items-start justify-between gap-4">
              <div>
                <Dialog.Title className="text-base font-bold text-[var(--danger)] flex items-center gap-1.5">
                  <AlertTriangle size={18} aria-hidden="true" />
                  <span>원문 소스 영구 삭제</span>
                </Dialog.Title>
                <Dialog.Description className="mt-1.5 text-xs text-[var(--muted)] leading-relaxed">
                  이 작업은 절대 되돌릴 수 없습니다.{" "}
                  <b className="text-[var(--fg)]">
                    &lsquo;{sourceToDelete?.title}&rsquo;
                  </b>{" "}
                  소스와 연관된 모든 청크 데이터, 검색 색인 좌표 및 원본 파일이
                  즉시 영구 삭제됩니다.
                </Dialog.Description>
              </div>
              <Dialog.Close asChild>
                <button
                  type="button"
                  className="icon-btn rounded-lg p-1 text-[var(--muted)] hover:bg-[var(--surface)] hover:text-[var(--fg)] transition-colors cursor-pointer"
                  aria-label="닫기"
                >
                  <X size={16} aria-hidden="true" />
                </button>
              </Dialog.Close>
            </div>

            {deleteError && (
              <p
                role="alert"
                className="invite-feedback error show mb-3 text-xs text-[var(--danger)]"
              >
                {deleteError}
              </p>
            )}

            <div className="modal-foot flex items-center justify-end gap-2 mt-6">
              <Dialog.Close asChild>
                <button
                  type="button"
                  disabled={Boolean(deletingId)}
                  className="button compact"
                >
                  취소
                </button>
              </Dialog.Close>
              <button
                type="button"
                disabled={Boolean(deletingId)}
                onClick={() =>
                  sourceToDelete && handleDeleteSource(sourceToDelete)
                }
                className="button compact danger"
                data-testid="confirm-delete-source-btn"
              >
                {Boolean(deletingId) && (
                  <Loader2 size={13} className="animate-spin" />
                )}
                <span>영구 삭제</span>
              </button>
            </div>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </div>
  );
}

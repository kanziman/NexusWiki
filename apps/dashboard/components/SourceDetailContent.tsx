"use client";

import * as Dialog from "@radix-ui/react-dialog";
import {
  AlertTriangle,
  AlignLeft,
  ArrowLeft,
  BookOpen,
  Check,
  ChevronRight,
  Code2,
  Copy,
  ExternalLink,
  Eye,
  FileCode,
  FileText,
  Hash,
  Layers,
  Loader2,
  Search,
  Sparkles,
  Trash2,
  X,
} from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { JobStepper } from "@/components/JobStepper";
import { MarkdownViewer } from "@/components/MarkdownViewer";
import { ApiError, apiFetch } from "@/lib/api-client";
import { formatDate, formatRelativeTime } from "@/lib/relative-time";
import { workspacePath } from "@/lib/workspace-path";

export type SourceChunkItem = {
  id: string;
  raw_source_id: string;
  chunk_index: number;
  char_start: number;
  char_end: number;
  content: string;
};

export type CitingWikiPageItem = {
  id: string;
  title: string;
  slug: string;
  category: string;
};

export type SourceDetailProps = {
  workspaceId: string;
  source: {
    id: string;
    title: string;
    source_type: string;
    mime_type?: string | null;
    byte_size?: number | null;
    content_hash?: string | null;
    created_at: string;
    content?: string | null;
  };
  chunks: SourceChunkItem[];
  citingPages: CitingWikiPageItem[];
  isOwner?: boolean;
};

function formatBytes(bytes?: number | null): string | null {
  if (bytes === null || bytes === undefined) return null;
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function getFormatBadge(
  title: string,
  mimeType?: string | null,
  sourceType?: string,
): { label: string; variant: string } {
  if (mimeType === "application/pdf" || title.toLowerCase().endsWith(".pdf")) {
    return { label: "PDF", variant: "pdf" };
  }
  if (
    mimeType === "text/markdown" ||
    title.toLowerCase().endsWith(".md") ||
    sourceType === "clipping"
  ) {
    return { label: "MD", variant: "md" };
  }
  return { label: "TXT", variant: "txt" };
}

function cleanPreviewText(text?: string | null): string {
  if (!text) return "";
  return text
    .replace(/<[^>]*>/g, " ")
    .replace(/^#+\s+/gm, "")
    .replace(/[-*=_~`#|]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

export function SourceDetailContent({
  workspaceId,
  source,
  chunks = [],
  citingPages = [],
  isOwner = false,
}: SourceDetailProps) {
  const router = useRouter();
  const isMdFormat =
    source.mime_type === "text/markdown" ||
    (source.title?.toLowerCase().endsWith(".md") ?? false) ||
    source.source_type === "clipping" ||
    (source.content?.includes("# ") ?? false) ||
    (source.content?.includes("| ") ?? false);

  const [selectedChunkIndex, setSelectedChunkIndex] = useState<number>(0);
  const [viewTab, setViewTab] = useState<"chunks" | "full">("chunks");
  const [fullRenderMode, setFullRenderMode] = useState<"rendered" | "raw">(
    isMdFormat ? "rendered" : "raw",
  );
  const [chunkRenderMode, setChunkRenderMode] = useState<"rendered" | "raw">(
    isMdFormat ? "rendered" : "raw",
  );
  const [chunkQuery, setChunkQuery] = useState("");
  const [copiedTitle, setCopiedTitle] = useState(false);
  const [copiedChunk, setCopiedChunk] = useState(false);
  const [copiedFull, setCopiedFull] = useState(false);

  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const format = getFormatBadge(
    source.title ?? "문서",
    source.mime_type,
    source.source_type,
  );
  const sizeFormatted = formatBytes(source.byte_size);
  const basePath = workspacePath(workspaceId);

  const filteredChunks = chunkQuery.trim()
    ? chunks.filter(
        (c) =>
          (c.content ?? "").toLowerCase().includes(chunkQuery.toLowerCase()) ||
          String(c.chunk_index + 1).includes(chunkQuery),
      )
    : chunks;

  const currentChunk =
    chunks.find((c) => c.chunk_index === selectedChunkIndex) ??
    chunks[0] ??
    null;

  const totalChars = (source.content?.length ?? 0).toLocaleString("ko-KR");
  const charStartMin =
    chunks.length > 0
      ? Math.min(...chunks.map((c) => c.char_start ?? 0)).toLocaleString(
          "ko-KR",
        )
      : "0";
  const charEndMax =
    chunks.length > 0
      ? Math.max(...chunks.map((c) => c.char_end ?? 0)).toLocaleString("ko-KR")
      : "0";

  function handleCopyTitle() {
    navigator.clipboard.writeText(source.title);
    setCopiedTitle(true);
    setTimeout(() => setCopiedTitle(false), 2000);
  }

  function handleCopyChunk(text?: string | null) {
    if (!text) return;
    navigator.clipboard.writeText(text);
    setCopiedChunk(true);
    setTimeout(() => setCopiedChunk(false), 2000);
  }

  function handleCopyFull(text?: string | null) {
    if (!text) return;
    navigator.clipboard.writeText(text);
    setCopiedFull(true);
    setTimeout(() => setCopiedFull(false), 2000);
  }

  async function handleDeleteSource() {
    if (!isOwner || deleting) return;
    setDeleting(true);
    setDeleteError(null);
    try {
      await apiFetch(`/workspaces/${workspaceId}/sources/${source.id}`, {
        method: "DELETE",
      });
      setDeleting(false);
      setDeleteOpen(false);
      router.push(`${basePath}/sources?deleted=true`);
    } catch (err: unknown) {
      setDeleting(false);
      setDeleteError(
        err instanceof ApiError && err.detail === "source_in_use"
          ? "이 원문을 참조하는 위키·공개본·대화 또는 진행 중 작업이 있습니다. 관련 항목을 먼저 정리해주세요."
          : "소스를 삭제하지 못했습니다. 다시 시도해주세요.",
      );
    }
  }

  return (
    <div
      className="content source-detail flex flex-col gap-6"
      data-od-id="source-detail-content"
    >
      {/* 1. 상단 브레드크럼 & 헤더 */}
      <section className="flex flex-col gap-3">
        <nav
          aria-label="라이브러리 탐색"
          className="flex items-center gap-2 text-xs font-semibold text-[var(--muted)]"
        >
          <Link
            href={`${basePath}/sources`}
            className="group nw-focus-ring inline-flex items-center gap-1.5 transition-colors hover:text-[var(--fg)]"
          >
            <ArrowLeft
              size={14}
              className="transition-transform group-hover:-translate-x-0.5"
              aria-hidden="true"
            />
            <span>원문 소스 목록</span>
          </Link>
          <ChevronRight
            size={13}
            className="text-[var(--border-strong)] opacity-60"
            aria-hidden="true"
          />
          <span className="text-[var(--fg)] font-medium truncate max-w-[320px]">
            {source.title}
          </span>
        </nav>

        <div className="rounded-2xl border border-[var(--border)] bg-[var(--bg)] p-5 sm:p-6 shadow-xs">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex flex-wrap items-center gap-2">
              <span className={`format ${format.variant}`}>{format.label}</span>
              {sizeFormatted ? (
                <span className="rounded-md border border-[var(--border)] bg-[var(--surface)] px-2 py-0.5 text-xs font-mono font-medium text-[var(--muted)]">
                  {sizeFormatted}
                </span>
              ) : null}
              <span className="rounded-md border border-[var(--border)] bg-[var(--surface)] px-2 py-0.5 text-xs font-mono font-medium text-[var(--muted)]">
                {source.source_type}
              </span>
              <span className="text-xs text-[var(--muted)]">
                {formatDate(source.created_at)} (
                {formatRelativeTime(source.created_at)})
              </span>
            </div>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={handleCopyTitle}
                className="nw-focus-ring inline-flex items-center gap-1.5 rounded-lg border border-[var(--border)] bg-[var(--surface)] px-2.5 py-1 text-xs font-medium text-[var(--muted)] hover:text-[var(--fg)] hover:border-[var(--accent)] transition-all cursor-pointer shadow-2xs"
                title="파일명 복사"
              >
                {copiedTitle ? (
                  <>
                    <Check size={12} className="text-[var(--good)]" />
                    <span className="text-[var(--good)]">복사됨</span>
                  </>
                ) : (
                  <>
                    <Copy size={12} />
                    <span>파일명 복사</span>
                  </>
                )}
              </button>

              {isOwner && (
                <button
                  type="button"
                  onClick={() => setDeleteOpen(true)}
                  className="nw-focus-ring inline-flex items-center gap-1.5 rounded-lg border border-[var(--danger)]/30 bg-[var(--surface)] px-2.5 py-1 text-xs font-medium text-[var(--danger)] hover:bg-[var(--danger-soft)] hover:border-[var(--danger)] transition-all cursor-pointer shadow-2xs"
                  title="원문 소스 삭제"
                  data-testid="delete-source-btn"
                >
                  <Trash2 size={12} />
                  <span>소스 삭제</span>
                </button>
              )}
            </div>
          </div>

          <h1
            className="mt-3.5 text-2xl font-bold tracking-tight text-[var(--fg)] break-all sm:text-3xl"
            data-od-id="source-title"
          >
            {source.title}
          </h1>
          <p className="mt-1.5 text-xs leading-relaxed text-[var(--muted)]">
            추출된 원본 텍스트의 5채널 검색 색인 좌표, 분할 청크 및 위키 문서
            인용 관계를 검토합니다.
          </p>
        </div>
      </section>

      {/* 2. 핵심 지표 통계 그리드 (3열 고품질 메트릭 타일) */}
      <section
        className="grid grid-cols-1 gap-3 sm:grid-cols-3"
        data-od-id="source-stats"
        aria-label="소스 상세 현황"
      >
        <div className="group rounded-2xl border border-[var(--border)] bg-[var(--bg)] p-4.5 shadow-xs transition-all hover:border-[var(--accent)] hover:shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-semibold text-[var(--muted)] uppercase tracking-wider">
              생성된 청크 수
            </span>
            <span className="flex h-6 w-6 items-center justify-center rounded-lg border border-[var(--border)] bg-[var(--surface)] text-[var(--accent)]">
              <Hash size={13} aria-hidden="true" />
            </span>
          </div>
          <b className="mt-2 block font-mono text-2xl font-bold tracking-tight text-[var(--fg)]">
            {String(chunks.length).padStart(2, "0")}
          </b>
          <div className="mt-1.5 flex items-center gap-1.5 text-[11px] text-[var(--muted)]">
            <span className="h-1.5 w-1.5 rounded-full bg-[var(--accent)]" />
            <span>검색에 사용하는 분할 청크</span>
          </div>
        </div>

        <div className="group rounded-2xl border border-[var(--border)] bg-[var(--bg)] p-4.5 shadow-xs transition-all hover:border-[var(--accent)] hover:shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-semibold text-[var(--muted)] uppercase tracking-wider">
              추출 문자 좌표 범위
            </span>
            <span className="flex h-6 w-6 items-center justify-center rounded-lg border border-[var(--border)] bg-[var(--surface)] text-[var(--accent)]">
              <AlignLeft size={13} aria-hidden="true" />
            </span>
          </div>
          <b className="mt-2 block font-mono text-xl font-bold tracking-tight text-[var(--fg)] truncate">
            {charStartMin} → {charEndMax}
          </b>
          <div className="mt-1.5 flex items-center gap-1.5 text-[11px] text-[var(--muted)]">
            <span className="h-1.5 w-1.5 rounded-full bg-[var(--accent)]" />
            <span>총 {totalChars}자 원본 추출</span>
          </div>
        </div>

        <div className="group rounded-2xl border border-[var(--border)] bg-[var(--bg)] p-4.5 shadow-xs transition-all hover:border-[var(--accent)] hover:shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-semibold text-[var(--muted)] uppercase tracking-wider">
              인용된 위키 문서
            </span>
            <span className="flex h-6 w-6 items-center justify-center rounded-lg border border-[var(--border)] bg-[var(--surface)] text-[var(--accent)]">
              <BookOpen size={13} aria-hidden="true" />
            </span>
          </div>
          <b className="mt-2 block font-mono text-2xl font-bold tracking-tight text-[var(--fg)]">
            {String(citingPages.length).padStart(2, "0")}
          </b>
          <div className="mt-1.5 flex items-center gap-1.5 text-[11px] text-[var(--muted)]">
            <span className="h-1.5 w-1.5 rounded-full bg-[var(--accent)]" />
            <span>위키 지식 베이스 연결됨</span>
          </div>
        </div>
      </section>

      {/* 3. 파이프라인 상태 & 인용 위키 문서 (2열 대칭 카드) */}
      <section className="grid grid-cols-1 gap-4 lg:grid-cols-12">
        {/* 파이프라인 인덱싱 상태 */}
        <div className="rounded-2xl border border-[var(--border)] bg-[var(--bg)] p-5 shadow-xs lg:col-span-6 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-3.5 border-b border-[var(--border)]">
              <div className="flex items-center gap-2.5">
                <div className="flex h-7 w-7 items-center justify-center rounded-lg border border-[var(--border)] bg-[var(--surface)] text-[var(--accent)] shadow-2xs">
                  <Layers size={15} aria-hidden="true" />
                </div>
                <div>
                  <h2 className="text-xs font-bold tracking-tight text-[var(--fg)]">
                    파이프라인 인덱싱 상태
                  </h2>
                  <span className="text-[10px] text-[var(--muted)]">
                    5채널 하이브리드 검색 인덱스 진행 현황
                  </span>
                </div>
              </div>
            </div>

            <div className="py-4">
              <JobStepper workspaceId={workspaceId} rawSourceId={source.id} />
            </div>
          </div>
        </div>

        {/* 연결된 위키 문서 */}
        <div className="rounded-2xl border border-[var(--border)] bg-[var(--bg)] p-5 shadow-xs lg:col-span-6 flex flex-col">
          <div className="flex items-center justify-between pb-3.5 border-b border-[var(--border)]">
            <div className="flex items-center gap-2.5">
              <div className="flex h-7 w-7 items-center justify-center rounded-lg border border-[var(--border)] bg-[var(--surface)] text-[var(--accent)] shadow-2xs">
                <BookOpen size={15} aria-hidden="true" />
              </div>
              <div>
                <h2 className="text-xs font-bold tracking-tight text-[var(--fg)]">
                  연결된 위키 문서 ({citingPages.length})
                </h2>
                <span className="text-[10px] text-[var(--muted)]">
                  이 원문을 인용하여 자동 합성된 위키 페이지
                </span>
              </div>
            </div>
          </div>

          <div className="flex-1 pt-4">
            {citingPages.length === 0 ? (
              <div className="flex h-full min-h-[80px] items-center justify-center rounded-xl border border-dashed border-[var(--border)] bg-[var(--surface)]/40 p-4 text-center">
                <p className="text-xs text-[var(--muted)]">
                  아직 이 소스를 인용한 위키 문서가 없습니다. 백그라운드
                  컴파일이 완료되면 자동으로 연결됩니다.
                </p>
              </div>
            ) : (
              <div className="flex flex-col gap-2">
                {citingPages.map((page) => (
                  <Link
                    key={page.slug}
                    href={`${basePath}/wiki/${page.slug}`}
                    className="group flex items-center justify-between gap-3 rounded-xl border border-[var(--border)] bg-[var(--surface)]/50 px-3.5 py-2.5 text-xs font-semibold text-[var(--fg)] transition-all hover:border-[var(--accent)] hover:bg-[var(--soft)] hover:text-[var(--accent)] shadow-2xs hover:shadow-xs"
                    title={page.title}
                  >
                    <div className="flex min-w-0 items-center gap-2.5">
                      <BookOpen
                        size={13}
                        className="shrink-0 opacity-60 group-hover:text-[var(--accent)]"
                        aria-hidden="true"
                      />
                      <span className="truncate">{page.title}</span>
                    </div>
                    <ExternalLink
                      size={12}
                      className="shrink-0 opacity-40 transition-transform group-hover:translate-x-0.5 group-hover:opacity-100"
                      aria-hidden="true"
                    />
                  </Link>
                ))}
              </div>
            )}
          </div>
        </div>
      </section>

      {/* 4. 청크 인스펙터 & 원문 텍스트 뷰어 (Clean Canvas Architecture) */}
      <section className="rounded-2xl border border-[var(--border)] bg-[var(--bg)] shadow-xs overflow-hidden">
        {/* 상단 메인 탭 컨트롤 */}
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--border)] bg-[var(--surface)]/30 px-5 py-3.5">
          <div className="flex items-center gap-2.5">
            <div className="flex h-7 w-7 items-center justify-center rounded-lg border border-[var(--border)] bg-[var(--bg)] text-[var(--accent)] shadow-2xs">
              <Code2 size={15} aria-hidden="true" />
            </div>
            <div>
              <h2 className="text-xs font-bold tracking-tight text-[var(--fg)]">
                콘텐츠 &amp; 청크 인스펙터
              </h2>
              <span className="text-[10px] text-[var(--muted)]">
                5채널 검색 색인 좌표 및 청크별 세부 텍스트
              </span>
            </div>
          </div>

          <div className="flex items-center gap-1 rounded-xl border border-[var(--border)] bg-[var(--surface)] p-1">
            <button
              type="button"
              onClick={() => setViewTab("chunks")}
              aria-pressed={viewTab === "chunks"}
              className={`cursor-pointer rounded-lg px-3.5 py-1.5 text-xs font-semibold transition-all ${
                viewTab === "chunks"
                  ? "bg-[var(--bg)] text-[var(--fg)] shadow-xs font-bold"
                  : "text-[var(--muted)] hover:text-[var(--fg)]"
              }`}
            >
              분할 청크 ({chunks.length})
            </button>
            <button
              type="button"
              onClick={() => setViewTab("full")}
              aria-pressed={viewTab === "full"}
              className={`cursor-pointer rounded-lg px-3.5 py-1.5 text-xs font-semibold transition-all ${
                viewTab === "full"
                  ? "bg-[var(--bg)] text-[var(--fg)] shadow-xs font-bold"
                  : "text-[var(--muted)] hover:text-[var(--fg)]"
              }`}
            >
              추출된 전체 원문
            </button>
          </div>
        </div>

        {viewTab === "chunks" ? (
          chunks.length === 0 ? (
            <div className="p-12 text-center">
              <FileCode
                size={32}
                className="mx-auto text-[var(--muted)] opacity-50"
              />
              <p className="mt-2 text-xs font-semibold text-[var(--fg)]">
                추출된 청크가 없습니다
              </p>
              <p className="mt-1 text-[11px] text-[var(--muted)]">
                파이프라인 파싱 단계가 완료되면 청크 목록이 여기에 표시됩니다.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-12 min-h-[520px]">
              {/* 좌측: 청크 리스트 레일 */}
              <div className="border-b md:border-b-0 md:border-r border-[var(--border)] md:col-span-5 p-3.5 flex flex-col gap-2.5 bg-[var(--surface)]/20">
                <div className="relative">
                  <Search
                    size={14}
                    className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--muted)]"
                    aria-hidden="true"
                  />
                  <input
                    type="text"
                    aria-label="청크 검색"
                    value={chunkQuery}
                    onChange={(e) => setChunkQuery(e.target.value)}
                    placeholder="청크 번호 또는 내용 검색…"
                    className="w-full rounded-xl border border-[var(--border)] bg-[var(--bg)] pl-9 pr-8 py-2 text-xs text-[var(--fg)] placeholder:text-[var(--muted)]/60 outline-none focus:border-[var(--accent)] transition-all"
                  />
                  {chunkQuery ? (
                    <button
                      type="button"
                      onClick={() => setChunkQuery("")}
                      aria-label="청크 검색어 지우기"
                      className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[var(--muted)] hover:text-[var(--fg)] p-0.5 cursor-pointer"
                    >
                      <X size={13} />
                    </button>
                  ) : null}
                </div>

                <div className="flex-1 overflow-y-auto max-h-[520px] space-y-2 pr-1">
                  {filteredChunks.map((chunk) => {
                    const isSelected =
                      (currentChunk?.chunk_index ?? 0) === chunk.chunk_index;
                    return (
                      <button
                        key={chunk.id}
                        type="button"
                        onClick={() => setSelectedChunkIndex(chunk.chunk_index)}
                        aria-pressed={isSelected}
                        style={{ borderRadius: "10px" }}
                        className={`w-full text-left p-3 transition-colors cursor-pointer border ${
                          isSelected
                            ? "border-[var(--accent)] bg-[var(--surface)] text-[var(--fg)] font-medium"
                            : "border-[var(--border)] bg-[var(--bg)] hover:bg-[var(--surface)]/50 hover:border-[var(--border-strong)] text-[var(--fg)]"
                        }`}
                      >
                        <div className="flex items-center justify-between gap-1.5">
                          <b className="font-mono text-xs font-bold flex items-center gap-1.5 text-[var(--fg)]">
                            {isSelected ? (
                              <span
                                className="h-1.5 w-1.5 rounded-full bg-[var(--accent)]"
                                aria-hidden="true"
                              />
                            ) : null}
                            청크 #{chunk.chunk_index + 1}
                          </b>
                          <span className="rounded-md bg-[var(--bg)] border border-[var(--border)]/70 px-1.5 py-0.5 font-mono text-[10px] text-[var(--muted)]">
                            {(chunk.char_start ?? 0).toLocaleString("ko-KR")}–
                            {(chunk.char_end ?? 0).toLocaleString("ko-KR")}
                          </span>
                        </div>
                        <p className="mt-1.5 line-clamp-2 text-xs text-[var(--muted)] leading-relaxed break-all">
                          {cleanPreviewText(chunk.content)}
                        </p>
                      </button>
                    );
                  })}
                </div>

                {chunkQuery.trim() ? (
                  <div className="pt-2 border-t border-[var(--border)]/60 text-center text-[10px] text-[var(--muted)]">
                    검색 결과: 총 {filteredChunks.length}개 / 전체{" "}
                    {chunks.length}개
                  </div>
                ) : null}
              </div>

              {/* 우측: 선택된 청크 내용 상세 뷰어 (클린 캔버스 뷰) */}
              <div className="md:col-span-7 p-5 flex flex-col bg-[var(--bg)]">
                {currentChunk ? (
                  <>
                    <div className="flex flex-wrap items-center justify-between gap-2 pb-3.5 border-b border-[var(--border)]">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-mono text-xs font-bold text-[var(--fg)]">
                          청크 #{currentChunk.chunk_index + 1}
                        </span>
                        <span className="rounded-md border border-[var(--border)] bg-[var(--surface)] px-2 py-0.5 text-[11px] font-mono text-[var(--muted)]">
                          좌표:{" "}
                          {(currentChunk.char_start ?? 0).toLocaleString(
                            "ko-KR",
                          )}
                          –
                          {(currentChunk.char_end ?? 0).toLocaleString("ko-KR")}
                        </span>
                        <span className="rounded-md border border-[var(--border)] bg-[var(--surface)] px-2 py-0.5 text-[11px] font-mono text-[var(--muted)]">
                          {(currentChunk.content?.length ?? 0).toLocaleString(
                            "ko-KR",
                          )}{" "}
                          글자
                        </span>
                      </div>

                      <div className="flex items-center gap-2">
                        {/* 마크다운 렌더링 / 원문 토글 */}
                        <div className="flex items-center rounded-lg border border-[var(--border)] bg-[var(--surface)] p-0.5">
                          <button
                            type="button"
                            onClick={() => setChunkRenderMode("rendered")}
                            aria-pressed={chunkRenderMode === "rendered"}
                            className={`inline-flex items-center gap-1 rounded-md px-2 py-1 text-[11px] font-semibold transition-all cursor-pointer ${
                              chunkRenderMode === "rendered"
                                ? "bg-[var(--bg)] text-[var(--accent)] shadow-xs font-bold"
                                : "text-[var(--muted)] hover:text-[var(--fg)]"
                            }`}
                            title="마크다운 렌더링 뷰"
                          >
                            <Eye size={12} />
                            <span>렌더 뷰</span>
                          </button>
                          <button
                            type="button"
                            onClick={() => setChunkRenderMode("raw")}
                            aria-pressed={chunkRenderMode === "raw"}
                            className={`inline-flex items-center gap-1 rounded-md px-2 py-1 text-[11px] font-semibold transition-all cursor-pointer ${
                              chunkRenderMode === "raw"
                                ? "bg-[var(--bg)] text-[var(--accent)] shadow-xs font-bold"
                                : "text-[var(--muted)] hover:text-[var(--fg)]"
                            }`}
                            title="원문 코드 뷰"
                          >
                            <FileText size={12} />
                            <span>원문</span>
                          </button>
                        </div>

                        <button
                          type="button"
                          onClick={() => handleCopyChunk(currentChunk.content)}
                          className="nw-focus-ring inline-flex items-center gap-1.5 rounded-lg border border-[var(--border)] bg-[var(--surface)] px-2.5 py-1 text-xs font-semibold text-[var(--fg)] transition-all hover:bg-[var(--soft)] hover:border-[var(--accent)] cursor-pointer shadow-2xs"
                        >
                          {copiedChunk ? (
                            <>
                              <Check size={13} className="text-[var(--good)]" />
                              <span className="text-[var(--good)]">복사됨</span>
                            </>
                          ) : (
                            <>
                              <Copy size={13} className="text-[var(--muted)]" />
                              <span>복사</span>
                            </>
                          )}
                        </button>
                      </div>
                    </div>

                    <div className="mt-4 flex-1 overflow-y-auto max-h-[520px] pr-2">
                      {chunkRenderMode === "rendered" ? (
                        <div className="py-1">
                          <MarkdownViewer
                            content={currentChunk.content ?? ""}
                          />
                        </div>
                      ) : (
                        <pre className="w-full rounded-xl border border-[var(--border)] bg-[var(--surface)]/30 p-4 font-mono text-xs leading-relaxed text-[var(--fg)] whitespace-pre-wrap break-all select-text shadow-inner">
                          {currentChunk.content ?? ""}
                        </pre>
                      )}
                    </div>
                  </>
                ) : (
                  <div className="flex h-full items-center justify-center p-12 text-center text-xs text-[var(--muted)]">
                    확인할 청크를 좌측에서 선택하세요.
                  </div>
                )}
              </div>
            </div>
          )
        ) : (
          /* 전체 추출 원문 탭 */
          <div className="p-5">
            <div className="flex flex-wrap items-center justify-between gap-3 pb-3.5 border-b border-[var(--border)]">
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold text-[var(--fg)]">
                  추출된 원문 텍스트
                </span>
                <span className="rounded-md border border-[var(--border)] bg-[var(--surface)] px-2 py-0.5 text-[11px] font-mono text-[var(--muted)]">
                  총 {totalChars}자
                </span>
                {isMdFormat ? (
                  <span className="inline-flex items-center gap-1 rounded-md bg-[var(--soft)] px-2 py-0.5 text-[11px] font-semibold text-[var(--accent)] border border-[var(--accent)]/20">
                    <Sparkles size={11} />
                    <span>마크다운 문서</span>
                  </span>
                ) : null}
              </div>

              <div className="flex items-center gap-2">
                {/* 마크다운 렌더링 / 원시 코드 뷰 모드 토글 */}
                <div className="flex items-center rounded-xl border border-[var(--border)] bg-[var(--surface)] p-0.5">
                  <button
                    type="button"
                    onClick={() => setFullRenderMode("rendered")}
                    aria-pressed={fullRenderMode === "rendered"}
                    className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold transition-all cursor-pointer ${
                      fullRenderMode === "rendered"
                        ? "bg-[var(--bg)] text-[var(--accent)] shadow-xs font-bold"
                        : "text-[var(--muted)] hover:text-[var(--fg)]"
                    }`}
                  >
                    <Eye size={13} />
                    <span>마크다운 렌더 뷰</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => setFullRenderMode("raw")}
                    aria-pressed={fullRenderMode === "raw"}
                    className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold transition-all cursor-pointer ${
                      fullRenderMode === "raw"
                        ? "bg-[var(--bg)] text-[var(--accent)] shadow-xs font-bold"
                        : "text-[var(--muted)] hover:text-[var(--fg)]"
                    }`}
                  >
                    <FileText size={13} />
                    <span>원문 텍스트 (Raw)</span>
                  </button>
                </div>

                {source.content ? (
                  <button
                    type="button"
                    onClick={() => handleCopyFull(source.content ?? "")}
                    className="nw-focus-ring inline-flex items-center gap-1.5 rounded-lg border border-[var(--border)] bg-[var(--surface)] px-3 py-1.5 text-xs font-semibold text-[var(--fg)] transition-all hover:bg-[var(--soft)] hover:border-[var(--accent)] cursor-pointer shadow-2xs"
                  >
                    {copiedFull ? (
                      <>
                        <Check size={13} className="text-[var(--good)]" />
                        <span className="text-[var(--good)]">복사됨</span>
                      </>
                    ) : (
                      <>
                        <Copy size={13} className="text-[var(--muted)]" />
                        <span>전체 복사</span>
                      </>
                    )}
                  </button>
                ) : null}
              </div>
            </div>

            <div className="mt-4">
              {source.content ? (
                fullRenderMode === "rendered" ? (
                  <div className="w-full max-h-[600px] overflow-y-auto px-4 py-2">
                    <MarkdownViewer content={source.content ?? ""} />
                  </div>
                ) : (
                  <pre className="w-full rounded-xl border border-[var(--border)] bg-[var(--surface)]/30 p-5 font-mono text-xs leading-relaxed text-[var(--fg)] whitespace-pre-wrap break-all max-h-[600px] overflow-y-auto select-text shadow-inner">
                    {source.content ?? ""}
                  </pre>
                )
              ) : (
                <div className="rounded-2xl border border-dashed border-[var(--border)] p-12 text-center text-xs text-[var(--muted)]">
                  추출된 텍스트 내용이 없습니다.
                </div>
              )}
            </div>
          </div>
        )}
      </section>

      {/* 원문 소스 삭제 확인 모달 */}
      <Dialog.Root open={deleteOpen} onOpenChange={setDeleteOpen}>
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
                    &lsquo;{source.title}&rsquo;
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
                  disabled={deleting}
                  className="button compact"
                >
                  취소
                </button>
              </Dialog.Close>
              <button
                type="button"
                disabled={deleting}
                onClick={handleDeleteSource}
                className="button compact danger"
                data-testid="confirm-delete-source-btn"
              >
                {deleting && <Loader2 size={13} className="animate-spin" />}
                <span>영구 삭제</span>
              </button>
            </div>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </div>
  );
}

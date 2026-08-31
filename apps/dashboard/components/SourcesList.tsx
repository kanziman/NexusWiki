"use client";

import * as Dialog from "@radix-ui/react-dialog";
import {
  AlertTriangle,
  Loader2,
  Plus,
  Search,
  Sparkles,
  Trash2,
  X,
} from "lucide-react";
import Link from "next/link";
import React, { useState } from "react";

import { Dropzone } from "@/components/Dropzone";
import { JobStepper } from "@/components/JobStepper";
import { Pagination } from "@/components/Pagination";
import { apiFetch } from "@/lib/api-client";
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
  prefillTitle?: string;
  initialTab?: "text";
  isOwner?: boolean;
};

const EMPTY_HEADING = "아직 등록된 소스가 없습니다";
const EMPTY_BODY =
  "파일을 드래그하거나 URL/텍스트를 붙여넣어 첫 소스를 추가하세요.";

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

  const PAGE_SIZE = 8;

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
      setSources((prev) => prev.filter((s) => s.id !== target.id));
      setDeletingId(null);
      setSourceToDelete(null);
    } catch (err: unknown) {
      setDeletingId(null);
      setDeleteError(
        (err as { message?: string })?.message ||
          "소스를 삭제하지 못했습니다. 다시 시도해주세요.",
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
  const totalChunks = Object.values(chunkStats).reduce(
    (sum, stat) => sum + stat.count,
    0,
  );
  const indexedCount = sources.filter(
    (source) => (chunkStats[source.id]?.count ?? 0) > 0,
  ).length;

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

      {/* 요약 통계 (소스가 있을 때만 표시) */}
      {sources.length > 0 && (
        <section className="stats" data-od-id="pipeline-stats">
          <div className="stat">
            <b>{sources.length}</b>
            <span>총 등록 소스</span>
          </div>
          <div className="stat">
            <b>{totalChunks}</b>
            <span>생성된 청크</span>
          </div>
          <div className="stat">
            <b>
              {indexedCount}/{sources.length}
            </b>
            <span>청크 생성 완료 소스</span>
          </div>
        </section>
      )}

      {/* 툴바 & 테이블 섹션 */}
      <section data-od-id="source-table-section">
        {sources.length > 0 && (
          <div className="toolbar flex items-center justify-between gap-4">
            <nav className="tabs" role="tablist" aria-label="파일 형식 필터">
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
                  className={`tab ${activeMime === tab.id ? "active" : ""}`}
                >
                  {tab.label}
                </button>
              ))}
            </nav>

            {/* 검색창 */}
            <div className="relative w-full max-w-[280px] flex-none">
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
          <div className="table-wrap overflow-x-auto rounded-lg border border-[var(--border)] bg-[var(--bg)] mt-3">
            <table
              className="table w-full text-left border-collapse"
              id="sources-library"
            >
              <colgroup>
                <col style={{ width: "24%" }} />
                <col style={{ width: "18%" }} />
                <col style={{ width: "14%" }} />
                <col style={{ width: "23%" }} />
                <col style={{ width: "12%" }} />
                <col style={{ width: "9%" }} />
              </colgroup>
              <thead>
                <tr className="border-b border-[var(--border)] bg-[var(--surface)]/60 text-[11px] font-bold text-[var(--muted)] uppercase tracking-wider">
                  <th scope="col" className="py-2.5 px-4">
                    소스 파일
                  </th>
                  <th scope="col" className="py-2.5 px-4">
                    연결된 위키 문서
                  </th>
                  <th scope="col" className="py-2.5 px-4">
                    청크 및 좌표
                  </th>
                  <th scope="col" className="py-2.5 px-4">
                    파이프라인 상태
                  </th>
                  <th scope="col" className="py-2.5 px-4">
                    업로드
                  </th>
                  <th scope="col" className="py-2.5 px-4 text-right">
                    <span className="sr-only">작업</span>
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border)] text-xs">
                {paginatedSources.map((source) => {
                  const format = formatLabel(source);
                  const size = formatBytes(source.byte_size);
                  const stat = chunkStats[source.id];
                  const cited = citingPages[source.id] ?? [];

                  return (
                    <tr
                      key={source.id}
                      className="hover:bg-[var(--surface)]/40 transition-colors"
                    >
                      {/* 소스 파일 */}
                      <td className="py-3 px-4">
                        <div className="file flex items-center gap-2.5 min-w-0">
                          <span
                            className={`format ${format.variant} flex-none px-1.5 py-0.5 rounded font-mono text-[10px] font-bold uppercase border`}
                          >
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
                                className="text-[13px] font-bold text-[var(--fg)] group-hover:text-[var(--accent)] group-hover:underline transition-colors block truncate"
                              >
                                {source.title}
                              </b>
                            </Link>
                            <span className="block text-[11px] text-[var(--muted)] truncate mt-0.5">
                              {size ? `${size} · ` : ""}
                              {source.source_type}
                            </span>
                          </div>
                        </div>
                      </td>

                      {/* 연결된 위키 문서 */}
                      <td className="py-3 px-4">
                        {cited.length === 0 ? (
                          <span className="sub text-[11px] text-[var(--muted)] italic">
                            인용한 위키 없음
                          </span>
                        ) : (
                          <div className="doc-chips flex flex-wrap gap-1.5">
                            {cited.map((page) => (
                              <Link
                                key={page.slug}
                                href={`${workspacePath(workspaceId)}/wiki/${page.slug}`}
                                className="doc-chip"
                                title={page.title}
                              >
                                <span className="truncate">{page.title}</span>
                              </Link>
                            ))}
                          </div>
                        )}
                      </td>

                      {/* 청크 및 좌표 */}
                      <td className="py-3 px-4 whitespace-nowrap">
                        {stat ? (
                          <>
                            <b className="mono block text-[12.5px] font-bold text-[var(--fg)]">
                              {stat.count} 청크
                            </b>
                            <span className="sub block text-[10.5px] text-[var(--muted)] font-mono mt-0.5">
                              {stat.charStart.toLocaleString("ko-KR")}–
                              {stat.charEnd.toLocaleString("ko-KR")} char
                            </span>
                          </>
                        ) : (
                          <span className="sub text-[11px] text-[var(--muted)]">
                            청크 없음
                          </span>
                        )}
                      </td>

                      {/* 파이프라인 상태 */}
                      <td className="py-3 px-4">
                        <JobStepper
                          workspaceId={workspaceId}
                          rawSourceId={source.id}
                        />
                      </td>

                      {/* 업로드 일시 */}
                      <td className="py-3 px-4 whitespace-nowrap">
                        <span className="block text-xs font-medium text-[var(--fg)]">
                          {formatRelativeTime(source.created_at)}
                        </span>
                        <span className="sub block text-[10.5px] text-[var(--muted)] mt-0.5">
                          {formatDate(source.created_at)}
                        </span>
                      </td>

                      {/* 작업 (상세 보기 & 삭제) */}
                      <td className="py-3 px-4 text-right whitespace-nowrap">
                        <div className="flex items-center justify-end gap-2">
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
                              className="nw-focus-ring inline-flex items-center p-1 rounded text-[var(--muted)] hover:text-[var(--danger)] hover:bg-[var(--danger-soft)] transition-colors cursor-pointer"
                              title="원문 소스 삭제"
                              data-testid={`delete-source-btn-${source.id}`}
                            >
                              <Trash2 size={13} aria-hidden="true" />
                              <span className="sr-only">삭제</span>
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
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

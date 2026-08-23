"use client";

import * as Dialog from "@radix-ui/react-dialog";
import { Plus, Search, X } from "lucide-react";
import Link from "next/link";
import React, { useState } from "react";

import { Dropzone } from "@/components/Dropzone";
import { JobStepper } from "@/components/JobStepper";
import { Pagination } from "@/components/Pagination";
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
}: SourcesListProps) {
  const [sources, setSources] = useState<SourceRow[]>(initialSources);
  const [activeMime, setActiveMime] = useState<MimeFilter>("all");
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);
  const [uploadOpen, setUploadOpen] = useState(
    Boolean(prefillTitle) || initialTab === "text",
  );

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
        <button
          type="button"
          className="button primary inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg shadow-xs"
          onClick={() => setUploadOpen(true)}
          data-od-id="upload-open"
        >
          <Plus size={14} aria-hidden="true" />
          <span>소스 업로드</span>
        </button>
      </section>

      {/* 요약 통계 */}
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

      {/* 툴바 & 테이블 섹션 */}
      <section data-od-id="source-table-section">
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

        {filteredSources.length === 0 ? (
          <div className="table-wrap p-12 text-center border border-[var(--border)] rounded-lg bg-[var(--surface)]/30 mt-3">
            <b className="block text-[14px] text-[var(--fg)]">
              {sources.length === 0
                ? EMPTY_HEADING
                : "해당 조건의 소스가 없습니다"}
            </b>
            <span className="mt-1.5 block text-xs text-[var(--muted)]">
              {sources.length === 0
                ? EMPTY_BODY
                : "다른 형식 탭을 선택하거나 검색어를 지우세요."}
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

                      {/* 작업 (상세 보기) */}
                      <td className="py-3 px-4 text-right whitespace-nowrap">
                        <Link
                          href={`${workspacePath(workspaceId)}/sources/${source.id}`}
                          className="text-button inline-flex items-center gap-0.5 text-xs font-semibold text-[var(--accent)] hover:underline"
                        >
                          <span>상세 보기</span>
                        </Link>
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
          <Dialog.Overlay className="modal-backdrop fixed inset-0 z-50 bg-black/40 backdrop-blur-xs transition-opacity" />
          <Dialog.Content className="modal fixed top-1/2 left-1/2 z-50 w-[min(540px,calc(100vw-32px))] max-h-[88vh] -translate-x-1/2 -translate-y-1/2 overflow-y-auto rounded-2xl border border-[var(--border)] bg-[var(--bg)] p-6 shadow-2xl outline-none">
            <div className="modal-head mb-5 flex items-start justify-between gap-4">
              <div>
                <Dialog.Title className="text-base font-bold text-[var(--fg)] tracking-tight">
                  소스 업로드
                </Dialog.Title>
                <p className="mt-1 text-xs text-[var(--muted)]">
                  파일, 웹 URL 또는 텍스트를 등록하여 위키 지식 베이스를
                  확장합니다.
                </p>
              </div>
              <Dialog.Close asChild>
                <button
                  type="button"
                  className="icon-btn rounded-lg p-1 text-[var(--muted)] hover:bg-[var(--surface)] hover:text-[var(--fg)] transition-colors"
                  aria-label="닫기"
                >
                  <X size={16} aria-hidden="true" />
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
    </div>
  );
}

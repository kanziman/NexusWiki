"use client";

import { File, FileText, Link2 } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import {
  EmptyState,
  PageHeader,
  StatusBadge,
} from "@/components/DashboardPrimitives";
import { Dropzone } from "@/components/Dropzone";
import { JobStepper } from "@/components/JobStepper";
import { createClient } from "@/lib/supabase/client";
import { workspacePath } from "@/lib/workspace-path";

export type SourceRow = {
  id: string;
  title: string;
  source_type: string;
  mime_type?: string | null;
  created_at: string;
  content_hash: string;
};

export type SourcesListProps = {
  workspaceId: string;
  initialSources: SourceRow[];
  prefillTitle?: string;
  initialTab?: "text";
};

const EMPTY_HEADING = "아직 등록된 소스가 없습니다";
const EMPTY_BODY =
  "파일을 드래그하거나 URL/텍스트를 붙여넣어 첫 소스를 추가하세요.";

const SOURCE_ICONS: Record<string, typeof File> = {
  file: File,
  url: Link2,
  text: FileText,
};

const SELECT_COLUMNS = "id,title,source_type,mime_type,created_at,content_hash";

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("ko-KR", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

type MimeFilter = "all" | "pdf" | "text_md";

export function SourcesList({
  workspaceId,
  initialSources,
  prefillTitle,
  initialTab,
}: SourcesListProps) {
  const [sources, setSources] = useState<SourceRow[]>(initialSources);
  const [activeMime, setActiveMime] = useState<MimeFilter>("all");

  async function handleIngested(_jobId: string, rawSourceId: string) {
    const supabase = createClient();
    const { data } = await supabase
      .from("raw_sources")
      .select(SELECT_COLUMNS)
      .eq("id", rawSourceId)
      .single<SourceRow>();

    if (data) {
      setSources((prev) => [data, ...prev]);
    }
  }

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

  const filteredSources = sources.filter((source) => {
    if (activeMime === "all") return true;
    if (activeMime === "pdf") return isPdf(source);
    if (activeMime === "text_md") return isTextMd(source);
    return true;
  });

  const pdfCount = sources.filter(isPdf).length;
  const textMdCount = sources.filter(isTextMd).length;

  return (
    <div className="mx-auto flex w-full max-w-4xl flex-col gap-xxl">
      <PageHeader
        title="Sources"
        description="생각의 근거가 되는 자료를 모으고, 연결하고, 다시 찾으세요."
      />

      <Dropzone
        workspaceId={workspaceId}
        onIngested={handleIngested}
        prefillTitle={prefillTitle}
        initialTab={initialTab}
      />

      {/* SRC-03: MIME 타입 3종 필터 탭 */}
      <div
        role="tablist"
        aria-label="소스 형식 필터"
        className="flex gap-xs border-b border-[var(--border)] bg-[var(--surface)] p-1 rounded-lg"
      >
        <button
          type="button"
          role="tab"
          aria-selected={activeMime === "all"}
          onClick={() => setActiveMime("all")}
          className={`min-h-8 cursor-pointer rounded-md px-3 text-xs font-semibold outline-none transition-colors ${
            activeMime === "all"
              ? "bg-[var(--bg)] text-[var(--accent)] shadow-sm"
              : "text-[var(--muted)] hover:text-[var(--fg)]"
          }`}
        >
          전체 ({sources.length})
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={activeMime === "pdf"}
          onClick={() => setActiveMime("pdf")}
          className={`min-h-8 cursor-pointer rounded-md px-3 text-xs font-semibold outline-none transition-colors ${
            activeMime === "pdf"
              ? "bg-[var(--bg)] text-[var(--accent)] shadow-sm"
              : "text-[var(--muted)] hover:text-[var(--fg)]"
          }`}
        >
          PDF ({pdfCount})
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={activeMime === "text_md"}
          onClick={() => setActiveMime("text_md")}
          className={`min-h-8 cursor-pointer rounded-md px-3 text-xs font-semibold outline-none transition-colors ${
            activeMime === "text_md"
              ? "bg-[var(--bg)] text-[var(--accent)] shadow-sm"
              : "text-[var(--muted)] hover:text-[var(--fg)]"
          }`}
        >
          텍스트/마크다운 ({textMdCount})
        </button>
      </div>

      {filteredSources.length === 0 ? (
        <EmptyState
          title={
            sources.length === 0 ? EMPTY_HEADING : "해당 형식의 소스가 없습니다"
          }
          detail={
            sources.length === 0
              ? EMPTY_BODY
              : "다른 형식 탭을 선택하거나 새 소스를 업로드하세요."
          }
        />
      ) : (
        <ul
          id="sources-library"
          className="flex flex-col border-y border-[var(--nw-rule)]"
        >
          {filteredSources.map((source) => {
            const Icon = SOURCE_ICONS[source.source_type] ?? File;
            return (
              <li
                key={source.id}
                className="flex flex-col gap-base border-b border-[var(--nw-rule)] py-lg last:border-b-0"
              >
                <div className="flex flex-col gap-sm sm:flex-row sm:items-center">
                  <div className="flex min-w-0 flex-1 items-center gap-sm">
                    <Icon
                      size={18}
                      aria-hidden="true"
                      className="shrink-0 text-[var(--nw-muted)]"
                    />
                    <span
                      title={source.title}
                      aria-label={source.title}
                      className="min-w-0 flex-1 truncate text-base font-semibold tracking-[-0.02em] text-[var(--nw-ink)]"
                    >
                      {source.title}
                    </span>
                  </div>
                  <div className="flex items-center gap-sm">
                    <StatusBadge>{formatDate(source.created_at)}</StatusBadge>
                    <Link
                      href={`${workspacePath(workspaceId)}/sources/${source.id}`}
                      className="nw-focus-ring rounded-sm border border-[var(--nw-rule-strong)] px-sm py-xs text-sm text-[var(--nw-ink)]"
                    >
                      상세 보기
                    </Link>
                  </div>
                </div>
                <JobStepper workspaceId={workspaceId} rawSourceId={source.id} />
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

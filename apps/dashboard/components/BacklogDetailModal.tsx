"use client";

import * as Dialog from "@radix-ui/react-dialog";
import { ChevronRight, FileText, Plus, X } from "lucide-react";
import Link from "next/link";
import React from "react";

import { formatDate } from "@/lib/relative-time";
import { workspacePath } from "@/lib/workspace-path";
import type { BacklogItem } from "./BacklogList";

export type BacklogDetailModalProps = {
  workspaceId: string;
  item: BacklogItem | null;
  onClose: () => void;
};

function escapeRegExp(string: string) {
  return string.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

/**
 * 마크다운 원시 기호들을 부드럽게 정돈하면서 대상 키워드 하이라이트를 유지한다.
 */
function renderCleanHighlightedExcerpt(excerpt: string, keywords: string[]) {
  // 1. 헤딩 기호, 볼드 기호, 인용 기호 등 과도한 마크다운 문법을 가볍게 정돈
  const cleaned = excerpt
    .replace(/^#{1,6}\s+/gm, "")
    .replace(/(\*\*|__)(.*?)\1/g, "$2")
    .replace(/^>\s?/gm, "")
    .replace(/^[*-]\s+/gm, "• ");

  const validKeywords = Array.from(
    new Set(keywords.map((k) => k.trim()).filter((k) => k.length > 0)),
  );
  if (validKeywords.length === 0) return cleaned;

  const pattern = new RegExp(
    `(${validKeywords.map((k) => escapeRegExp(k)).join("|")})`,
    "gi",
  );
  const parts = cleaned.split(pattern);

  return parts.map((part, i) => {
    const isMatch = validKeywords.some(
      (k) => k.toLowerCase() === part.toLowerCase(),
    );
    if (isMatch) {
      return (
        <mark
          key={i}
          className="bg-[var(--danger)]/15 text-[var(--danger)] font-bold px-1 py-0.5 rounded not-italic border border-[var(--danger)]/25"
        >
          {part}
        </mark>
      );
    }
    return part;
  });
}

export function BacklogDetailModal({
  workspaceId,
  item,
  onClose,
}: BacklogDetailModalProps) {
  const displayTitle = item?.display_title || item?.target_slug || "";
  const firstDetected = item?.first_detected_at
    ? formatDate(item.first_detected_at)
    : "최근";
  const referencingPages = item?.referencing_pages ?? [];
  const highlightKeywords = item
    ? [item.display_title, item.target_slug].filter(Boolean)
    : [];

  return (
    <Dialog.Root
      open={item !== null}
      onOpenChange={(open) => {
        if (!open) onClose();
      }}
    >
      <Dialog.Portal>
        <Dialog.Overlay className="modal-backdrop fixed inset-0 z-50 bg-black/40 backdrop-blur-xs transition-opacity" />
        <Dialog.Content className="modal backlog-panel fixed top-1/2 left-1/2 z-50 w-[min(540px,calc(100vw-32px))] max-h-[86vh] -translate-x-1/2 -translate-y-1/2 overflow-y-auto rounded-2xl border border-[var(--border)] bg-[var(--bg)] p-6 shadow-2xl outline-none">
          {item ? (
            <>
              {/* 모달 헤더 */}
              <div className="modal-head mb-3 flex items-start justify-between gap-4">
                <div className="min-w-0 flex-1">
                  <Dialog.Title className="text-lg font-bold text-[var(--fg)] tracking-tight truncate">
                    {displayTitle}
                  </Dialog.Title>
                  <div className="flex flex-wrap items-center gap-2 mt-1.5">
                    {displayTitle !== item.target_slug ? (
                      <>
                        <span className="backlog-panel-slug font-mono text-[11px] text-[var(--muted)] bg-[var(--surface)] border border-[var(--border)] px-1.5 py-0.5 rounded">
                          {item.target_slug}
                        </span>
                        <span className="text-[11px] text-[var(--muted)] opacity-60">
                          ·
                        </span>
                      </>
                    ) : null}
                    <span className="backlog-panel-meta text-xs text-[var(--muted)]">
                      최초 감지 · {firstDetected}
                    </span>
                  </div>
                </div>
                <Dialog.Close asChild>
                  <button
                    type="button"
                    className="icon-btn rounded-lg p-1.5 text-[var(--muted)] hover:bg-[var(--surface)] hover:text-[var(--fg)] transition-colors"
                    aria-label="닫기"
                  >
                    <X size={16} aria-hidden="true" />
                  </button>
                </Dialog.Close>
              </div>

              {/* 인용 중인 위키 문서 목록 */}
              <div className="backlog-panel-refs mt-5">
                <div className="flex items-center justify-between mb-2.5">
                  <h3 className="text-xs font-bold text-[var(--muted)] uppercase tracking-wider">
                    인용 중인 위키 {referencingPages.length}
                  </h3>
                </div>

                {referencingPages.length === 0 ? (
                  <div className="p-6 text-center rounded-xl border border-dashed border-[var(--border-strong)] bg-[var(--surface)]/30">
                    <p className="sub text-xs text-[var(--muted)]">
                      인용 문서 없음
                    </p>
                  </div>
                ) : (
                  <ul className="space-y-2.5">
                    {referencingPages.map((page) => (
                      <li key={page.id}>
                        <Link
                          href={`${workspacePath(workspaceId)}/wiki/${page.slug}`}
                          className="font-bold text-[13px] text-[var(--fg)] hover:text-[var(--accent)] transition-colors flex items-center justify-between group"
                        >
                          <div className="flex items-center gap-2 min-w-0">
                            <FileText
                              size={13}
                              className="text-[var(--accent)] flex-none"
                            />
                            <span className="truncate">{page.title}</span>
                          </div>
                          <ChevronRight
                            size={14}
                            className="text-[var(--muted)] group-hover:text-[var(--accent)] group-hover:translate-x-0.5 transition-all flex-none opacity-60 group-hover:opacity-100"
                          />
                        </Link>
                        {page.excerpt ? (
                          <p className="backlog-panel-excerpt">
                            {renderCleanHighlightedExcerpt(
                              page.excerpt,
                              highlightKeywords,
                            )}
                          </p>
                        ) : null}
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              {/* 모달 푸터 액션 */}
              <div className="modal-foot flex items-center justify-end mt-6 pt-4 border-t border-[var(--border)]">
                <Link
                  href={`${workspacePath(workspaceId)}/sources?prefillTitle=${encodeURIComponent(
                    displayTitle,
                  )}&tab=text`}
                  className="button primary inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-semibold shadow-xs"
                >
                  <Plus size={13} aria-hidden="true" />
                  <span>소스 추가</span>
                </Link>
              </div>
            </>
          ) : null}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

"use client";

import * as Dialog from "@radix-ui/react-dialog";
import { FileText, X } from "lucide-react";
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

function renderHighlightedExcerpt(excerpt: string, keywords: string[]) {
  const validKeywords = Array.from(
    new Set(keywords.map((k) => k.trim()).filter((k) => k.length > 0)),
  );
  if (validKeywords.length === 0) return excerpt;

  const pattern = new RegExp(
    `(${validKeywords.map((k) => escapeRegExp(k)).join("|")})`,
    "gi",
  );
  const parts = excerpt.split(pattern);

  return parts.map((part, i) => {
    const isMatch = validKeywords.some(
      (k) => k.toLowerCase() === part.toLowerCase(),
    );
    if (isMatch) {
      return (
        <mark
          key={i}
          className="bg-[var(--danger)]/15 text-[var(--danger)] font-bold px-1.5 py-0.5 rounded not-italic border border-[var(--danger)]/25"
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
        <Dialog.Overlay className="modal-backdrop fixed inset-0" />
        <Dialog.Content className="modal backlog-panel fixed top-1/2 left-1/2 max-h-[86vh] -translate-x-1/2 -translate-y-1/2 overflow-auto">
          {item ? (
            <>
              <div className="modal-head">
                <Dialog.Title>{displayTitle}</Dialog.Title>
                <Dialog.Close asChild>
                  <button type="button" className="icon-btn" aria-label="닫기">
                    <X size={16} aria-hidden="true" />
                  </button>
                </Dialog.Close>
              </div>
              <p className="backlog-panel-slug font-mono text-xs font-semibold text-[var(--danger)] bg-[var(--danger)]/10 border border-[var(--danger)]/20 px-2 py-0.5 rounded inline-block mt-1">
                {item.target_slug}
              </p>
              <p className="backlog-panel-meta text-xs text-[var(--muted)] mb-4 mt-2">
                최초 감지 · {firstDetected}
              </p>

              <div className="backlog-panel-refs">
                <h3 className="text-xs font-bold text-[var(--muted)] uppercase tracking-wider mb-2">
                  인용 중인 위키 {referencingPages.length}
                </h3>
                {referencingPages.length === 0 ? (
                  <p className="sub text-xs text-[var(--muted)]">
                    인용 문서 없음
                  </p>
                ) : (
                  <ul className="space-y-2">
                    {referencingPages.map((page) => (
                      <li
                        key={page.id}
                        className="p-2.5 rounded-lg border border-[var(--border)] bg-[var(--surface)]/40"
                      >
                        <Link
                          href={`${workspacePath(workspaceId)}/wiki/${page.slug}`}
                          className="font-semibold text-xs text-[var(--fg)] hover:text-[var(--accent)] transition-colors flex items-center gap-1.5"
                        >
                          <FileText size={12} className="opacity-70" />
                          <span>{page.title}</span>
                        </Link>
                        {page.excerpt ? (
                          <p className="backlog-panel-excerpt text-[11.5px] text-[var(--muted)] mt-1.5 pl-4 border-l-2 border-[var(--border)] leading-relaxed italic">
                            {renderHighlightedExcerpt(
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

              <div className="modal-foot mt-5">
                <Link
                  href={`${workspacePath(workspaceId)}/sources?prefillTitle=${encodeURIComponent(
                    displayTitle,
                  )}&tab=text`}
                  className="button primary"
                >
                  소스 추가
                </Link>
              </div>
            </>
          ) : null}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

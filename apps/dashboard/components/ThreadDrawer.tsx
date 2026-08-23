"use client";

import { MessageSquare, Pencil, Plus, Trash2 } from "lucide-react";
import React from "react";

import { formatRelativeTime } from "@/lib/relative-time";
import type { AskThreadSummary } from "@/lib/ask-threads";

export type ThreadDrawerProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  threads: AskThreadSummary[];
  activeThreadId: string | null;
  loading: boolean;
  error: string | null;
  onRetry: () => void;
  onSelect: (threadId: string) => void;
  onNew: () => void;
  onRename: (threadId: string, title: string) => void;
  onRequestRename?: (threadId: string, currentTitle: string) => void;
  onDelete: (threadId: string, title: string) => void;
};

export function ThreadDrawer({
  open,
  onOpenChange,
  threads,
  activeThreadId,
  loading,
  error,
  onRetry,
  onSelect,
  onNew,
  onRename,
  onRequestRename,
  onDelete,
}: ThreadDrawerProps) {
  if (!open) return null;

  function handleRenameClick(
    event: React.MouseEvent,
    thread: AskThreadSummary,
  ) {
    event.stopPropagation();
    event.preventDefault();

    try {
      if (
        typeof window !== "undefined" &&
        typeof window.prompt === "function"
      ) {
        const next = window.prompt("이름 바꾸기", thread.title);
        if (next !== null && next !== undefined) {
          if (next.trim().length > 0) {
            onRename(thread.id, next.trim());
          }
          return;
        }
      }
    } catch {
      // window.prompt 미지원 또는 에러 발생 시 모달 fallback
    }

    if (onRequestRename) {
      onRequestRename(thread.id, thread.title);
    }
  }

  return (
    <>
      {/* 모바일 / 좁은 화면용 스크림 오버레이 */}
      <div
        className="thread-drawer-scrim fixed inset-0 z-20 bg-black/30 backdrop-blur-2xs lg:hidden"
        onClick={() => onOpenChange(false)}
        aria-hidden="true"
      />

      <aside
        className="thread-drawer open flex flex-col h-full w-[280px] shrink-0 border-r border-[var(--border)] bg-[var(--bg)] z-30 transition-all select-none"
        aria-label="대화 이력 사이드바"
      >
        {/* 드로어 상단 헤더: 타이틀 + 새 대화 버튼 */}
        <div className="thread-drawer-head flex items-center justify-between p-3.5 border-b border-[var(--border)] shrink-0 bg-[var(--bg)]">
          <div className="flex items-center gap-2">
            <MessageSquare
              size={15}
              className="text-[var(--accent)]"
              aria-hidden="true"
            />
            <b className="text-xs font-bold text-[var(--fg)] tracking-tight">
              대화 목록
            </b>
          </div>
          <button
            type="button"
            className="button compact inline-flex items-center gap-1 text-xs font-semibold py-1 px-2.5 rounded-md border border-[var(--border)] bg-[var(--surface)] hover:bg-[var(--accent)] hover:text-white hover:border-[var(--accent)] transition-all shadow-2xs"
            onClick={onNew}
          >
            <Plus size={12} aria-hidden="true" />
            <span>새 대화</span>
          </button>
        </div>

        {/* 스레드 리스트 영역 */}
        <div className="flex-1 overflow-y-auto p-2.5 space-y-1">
          {loading ? (
            <div
              data-testid="thread-list-loading"
              className="thread-list-skeleton p-2 space-y-2"
            >
              <div className="h-11 rounded-md bg-[var(--surface)] animate-pulse" />
              <div className="h-11 rounded-md bg-[var(--surface)] animate-pulse" />
              <div className="h-11 rounded-md bg-[var(--surface)] animate-pulse" />
            </div>
          ) : error ? (
            <div className="answer notice p-3 text-xs" role="alert">
              <p className="mb-2 text-[var(--danger)]">
                대화 목록을 불러오지 못했습니다.
              </p>
              <button
                type="button"
                className="button compact text-xs"
                onClick={onRetry}
              >
                다시 시도
              </button>
            </div>
          ) : threads.length === 0 ? (
            <div className="py-12 px-4 text-center">
              <p className="thread-list-empty text-xs text-[var(--muted)]">
                아직 나눈 대화가 없습니다
              </p>
            </div>
          ) : (
            <div
              role="listbox"
              aria-label="대화 목록"
              className="thread-list space-y-1"
            >
              {threads.map((thread) => {
                const isActive = thread.id === activeThreadId;
                return (
                  <div
                    key={thread.id}
                    role="option"
                    aria-selected={isActive}
                    tabIndex={isActive ? 0 : -1}
                    className={`thread-list-item group relative flex flex-col gap-1 p-2.5 rounded-lg border transition-all cursor-pointer ${
                      isActive
                        ? "active bg-[var(--surface)] border-[var(--border-strong)] text-[var(--fg)] shadow-xs"
                        : "border-transparent hover:border-[var(--border)] hover:bg-[var(--surface)]/60 text-[var(--muted)] hover:text-[var(--fg)]"
                    }`}
                    onClick={() => onSelect(thread.id)}
                    onKeyDown={(event) => {
                      if (event.key === "Enter" || event.key === " ") {
                        event.preventDefault();
                        onSelect(thread.id);
                      }
                    }}
                  >
                    <span className="thread-list-title text-xs font-semibold truncate block pr-1 leading-snug">
                      {thread.title}
                    </span>
                    <div className="flex items-center justify-between gap-2 mt-0.5">
                      <span className="thread-list-time text-[10.5px] font-mono text-[var(--muted)] opacity-80">
                        {formatRelativeTime(thread.updated_at)}
                      </span>
                      <span className="thread-list-actions flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button
                          type="button"
                          className="button compact p-1 text-[var(--muted)] hover:text-[var(--fg)] hover:bg-[var(--bg)] rounded"
                          aria-label={`${thread.title} 대화 이름 바꾸기`}
                          title="이름 바꾸기"
                          onClick={(event) => handleRenameClick(event, thread)}
                        >
                          <Pencil size={11} aria-hidden="true" />
                          <span className="sr-only">이름 바꾸기</span>
                        </button>
                        <button
                          type="button"
                          className="button compact danger p-1 text-[var(--muted)] hover:text-[var(--danger)] hover:bg-[var(--bg)] rounded"
                          aria-label={`${thread.title} 대화 옵션`}
                          title="삭제"
                          onClick={(event) => {
                            event.stopPropagation();
                            onDelete(thread.id, thread.title);
                          }}
                        >
                          <Trash2 size={11} aria-hidden="true" />
                          <span className="sr-only">삭제</span>
                        </button>
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </aside>
    </>
  );
}

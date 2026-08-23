"use client";

import { PanelLeftClose, PanelLeftOpen } from "lucide-react";

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
  onDelete,
}: ThreadDrawerProps) {
  return (
    <>
      <button
        type="button"
        className="icon-btn"
        aria-label={open ? "대화 목록 닫기" : "대화 목록 열기"}
        aria-expanded={open}
        onClick={() => onOpenChange(!open)}
      >
        {open ? (
          <PanelLeftClose aria-hidden="true" size={18} />
        ) : (
          <PanelLeftOpen aria-hidden="true" size={18} />
        )}
      </button>
      {open ? (
        <div
          className="thread-drawer-scrim"
          onClick={() => onOpenChange(false)}
        />
      ) : null}
      <div className={`thread-drawer ${open ? "open" : ""}`} hidden={!open}>
        <div className="thread-drawer-head">
          <b>대화 목록</b>
          <button type="button" className="button compact" onClick={onNew}>
            새 대화
          </button>
        </div>
        {loading ? (
          <div
            data-testid="thread-list-loading"
            className="thread-list-skeleton"
          >
            <span />
            <span />
            <span />
          </div>
        ) : error ? (
          <div className="answer notice" role="alert">
            <p>대화 목록을 불러오지 못했습니다.</p>
            <button type="button" className="button compact" onClick={onRetry}>
              다시 시도
            </button>
          </div>
        ) : threads.length === 0 ? (
          <p className="thread-list-empty">아직 나눈 대화가 없습니다</p>
        ) : (
          <div role="listbox" aria-label="대화 목록" className="thread-list">
            {threads.map((thread) => (
              <div
                key={thread.id}
                role="option"
                aria-selected={thread.id === activeThreadId}
                tabIndex={thread.id === activeThreadId ? 0 : -1}
                className={`thread-list-item ${thread.id === activeThreadId ? "active" : ""}`}
                onClick={() => onSelect(thread.id)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    onSelect(thread.id);
                  }
                }}
              >
                <span className="thread-list-title">{thread.title}</span>
                <span className="thread-list-time">
                  {formatRelativeTime(thread.updated_at)}
                </span>
                <span className="thread-list-actions">
                  <button
                    type="button"
                    className="button compact"
                    aria-label={`${thread.title} 대화 이름 바꾸기`}
                    onClick={(event) => {
                      event.stopPropagation();
                      const next = window.prompt("이름 바꾸기", thread.title);
                      if (next && next.trim()) onRename(thread.id, next.trim());
                    }}
                  >
                    이름 바꾸기
                  </button>
                  <button
                    type="button"
                    className="button compact danger"
                    aria-label={`${thread.title} 대화 옵션`}
                    onClick={(event) => {
                      event.stopPropagation();
                      onDelete(thread.id, thread.title);
                    }}
                  >
                    삭제
                  </button>
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </>
  );
}

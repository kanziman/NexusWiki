"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Fragment, useEffect, useRef, useState } from "react";
import { PanelLeftClose, PanelLeftOpen } from "lucide-react";
import * as Dialog from "@radix-ui/react-dialog";

import { MarkdownAnswer } from "@/components/MarkdownAnswer";
import { ThreadDrawer } from "@/components/ThreadDrawer";
import {
  splitTextWithAnchors,
  type AnchorPart,
  type ResolvedAnchor,
  type TextPart,
} from "@/lib/citation-anchors";
import { ApiError } from "@/lib/api-client";
import {
  deleteAskThread,
  getAskThread,
  listAskThreads,
  renameAskThread,
  type AskThreadMessage,
  type AskThreadSummary,
} from "@/lib/ask-threads";
import { requireEnv } from "@/lib/env";
import { parseSseStream } from "@/lib/sse";
import { createClient } from "@/lib/supabase/client";
import { workspacePath } from "@/lib/workspace-path";

export type AskConversationProps = { workspaceId: string };

type PromptTemplate = { id: string; name: string };

type TurnStatus =
  "streaming" | "resolved" | "no-evidence" | "error" | "dropped";

type Turn = {
  question: string;
  segments: (TextPart | AnchorPart)[];
  status: TurnStatus;
  errorToken?: string;
  missingChannelsNotice: boolean;
  persisted?: boolean;
};

const EMPTY_HEADING = "무엇이든 물어보세요";
const EMPTY_BODY = "워크스페이스에 등록된 소스와 위키에서 답을 찾아드립니다.";
const NO_EVIDENCE_MESSAGE = "근거를 찾지 못했습니다.";
const MISSING_CHANNELS_NOTICE =
  "일부 검색 채널을 사용할 수 없어 답변이 불완전할 수 있습니다.";
const STREAM_DROP_MESSAGE = "연결이 끊어졌습니다. 다시 시도해주세요.";
const GENERIC_ERROR_MESSAGE =
  "질문에 답하지 못했습니다. 잠시 후 다시 시도해주세요.";
const REQUESTED_K = 8;
const DRAFT_PREFIX = "draft:";

function newDraftKey(): string {
  return `${DRAFT_PREFIX}${crypto.randomUUID()}`;
}

function newClientTurnId(): string {
  return crypto.randomUUID();
}

async function readAskErrorToken(response: Response): Promise<string> {
  try {
    const text = await response.text();
    if (text.length === 0) return "unknown_error";
    const parsed: unknown = JSON.parse(text);
    if (
      parsed !== null &&
      typeof parsed === "object" &&
      "detail" in parsed &&
      typeof (parsed as { detail: unknown }).detail === "string"
    ) {
      return (parsed as { detail: string }).detail;
    }
    return "unknown_error";
  } catch {
    return "unknown_error";
  }
}

function turnsFromMessages(messages: AskThreadMessage[]): Turn[] {
  return messages.map((message) => {
    if (message.status === "no-evidence") {
      return {
        question: message.question,
        segments: [],
        status: "no-evidence" as const,
        missingChannelsNotice: false,
        persisted: true,
      };
    }
    if (message.status === "error") {
      return {
        question: message.question,
        segments: [],
        status: "error" as const,
        missingChannelsNotice: false,
        persisted: true,
      };
    }
    const citations = message.citations ?? {
      text: message.answer_text,
      resolved: [],
    };
    return {
      question: message.question,
      segments: splitTextWithAnchors(
        citations.text || message.answer_text,
        citations.resolved ?? [],
      ),
      status: "resolved" as const,
      missingChannelsNotice: false,
      persisted: true,
    };
  });
}

export function AskConversation({ workspaceId }: AskConversationProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [templates, setTemplates] = useState<PromptTemplate[]>([]);
  const [templateId, setTemplateId] = useState<string | undefined>(undefined);
  const [question, setQuestion] = useState("");
  const [conversations, setConversations] = useState<Record<string, Turn[]>>(
    {},
  );
  const [activeKey, setActiveKey] = useState(() => newDraftKey());
  const [submittingKeys, setSubmittingKeys] = useState<Record<string, boolean>>(
    {},
  );
  const [threads, setThreads] = useState<AskThreadSummary[]>([]);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [listLoading, setListLoading] = useState(true);
  const [listError, setListError] = useState<string | null>(null);
  const [restoreError, setRestoreError] = useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<{
    id: string;
    title: string;
  } | null>(null);
  const autoSubmittedRef = useRef(false);
  const activeKeyRef = useRef(activeKey);
  activeKeyRef.current = activeKey;

  const turns = conversations[activeKey] ?? [];
  const submitting = Boolean(submittingKeys[activeKey]);
  const activeThreadId = activeKey.startsWith(DRAFT_PREFIX) ? null : activeKey;

  const initialQuery =
    searchParams?.get("q") ?? searchParams?.get("question") ?? "";
  const initialThread = searchParams?.get("thread") ?? "";

  async function refreshThreads() {
    setListLoading(true);
    setListError(null);
    try {
      const rows = await listAskThreads(workspaceId);
      setThreads(rows);
    } catch {
      setListError("load_failed");
    } finally {
      setListLoading(false);
    }
  }

  useEffect(() => {
    void refreshThreads();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [workspaceId]);

  useEffect(() => {
    const trimmed = initialQuery.trim();
    if (!trimmed || autoSubmittedRef.current) return;
    autoSubmittedRef.current = true;
    void submitQuestion(trimmed, activeKeyRef.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialQuery]);

  useEffect(() => {
    if (!initialThread) return;
    void openThread(initialThread);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialThread]);

  useEffect(() => {
    let cancelled = false;

    async function loadTemplates() {
      const supabase = createClient();
      const { data } = await supabase
        .from("prompt_templates")
        .select("id,name")
        .eq("target_type", "ask")
        .or(`workspace_id.is.null,workspace_id.eq.${workspaceId}`);
      if (!cancelled && data) {
        setTemplates(data as PromptTemplate[]);
      }
    }

    loadTemplates();
    return () => {
      cancelled = true;
    };
  }, [workspaceId]);

  function patchConversation(key: string, updater: (prev: Turn[]) => Turn[]) {
    setConversations((prev) => ({
      ...prev,
      [key]: updater(prev[key] ?? []),
    }));
  }

  async function openThread(threadId: string) {
    setRestoreError(null);
    try {
      const detail = await getAskThread(workspaceId, threadId);
      patchConversation(threadId, () => turnsFromMessages(detail.messages));
      setActiveKey(threadId);
      setThreads((prev) => {
        if (prev.some((row) => row.id === detail.id)) {
          return prev.map((row) => (row.id === detail.id ? detail : row));
        }
        return [detail, ...prev];
      });
    } catch (error) {
      setRestoreError(
        error instanceof ApiError && error.status === 403
          ? "deleted"
          : "load_failed",
      );
    }
  }

  async function submitQuestion(text: string, conversationKey: string) {
    const trimmed = text.trim();
    if (trimmed.length === 0 || submittingKeys[conversationKey]) return;

    const turnIndex = (conversations[conversationKey] ?? []).length;
    const clientTurnId = newClientTurnId();
    const threadId = conversationKey.startsWith(DRAFT_PREFIX)
      ? undefined
      : conversationKey;

    setSubmittingKeys((prev) => ({ ...prev, [conversationKey]: true }));
    patchConversation(conversationKey, (prev) => [
      ...prev,
      {
        question: trimmed,
        segments: [],
        status: "streaming",
        missingChannelsNotice: false,
      },
    ]);

    function patchTurn(patch: Partial<Turn>) {
      patchConversation(conversationKey, (prev) => {
        if (prev[turnIndex] === undefined) return prev;
        const next = [...prev];
        next[turnIndex] = { ...next[turnIndex], ...patch };
        return next;
      });
    }

    let accumulatedText = "";
    let noEvidence = false;

    try {
      const supabase = createClient();
      const {
        data: { session },
      } = await supabase.auth.getSession();
      if (!session) {
        throw new Error("apiFetch called without an active session");
      }

      const response = await fetch(
        `${requireEnv("NEXT_PUBLIC_API_URL")}/workspaces/${workspaceId}/ask`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${session.access_token}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            query: trimmed,
            requested_k: REQUESTED_K,
            template_id: templateId,
            client_turn_id: clientTurnId,
            ...(threadId ? { thread_id: threadId } : {}),
          }),
        },
      );

      if (!response.ok) {
        const errorToken = await readAskErrorToken(response);
        patchTurn({ status: "error", errorToken });
        return;
      }

      for await (const frame of parseSseStream(response)) {
        if (frame.event === "meta") {
          const meta = frame.data as {
            no_evidence?: boolean;
            missing_channels?: string[];
          };
          if (meta.no_evidence) {
            noEvidence = true;
          }
          if (meta.missing_channels && meta.missing_channels.length > 0) {
            patchTurn({ missingChannelsNotice: true });
          }
        } else if (frame.event === "delta") {
          const delta = frame.data as { text: string };
          accumulatedText += delta.text;
          patchTurn({ segments: splitTextWithAnchors(accumulatedText) });
        } else if (frame.event === "citations") {
          const citations = frame.data as {
            text?: string;
            resolved?: ResolvedAnchor[];
            error?: string;
          };
          if (noEvidence) {
            patchTurn({ status: "no-evidence" });
          } else if (citations.error) {
            patchTurn({ status: "error", errorToken: citations.error });
          } else {
            accumulatedText = citations.text ?? accumulatedText;
            patchTurn({
              status: "resolved",
              segments: splitTextWithAnchors(
                accumulatedText,
                citations.resolved ?? [],
              ),
            });
          }
        } else if (frame.event === "done") {
          const done = frame.data as { thread_id?: string };
          if (done.thread_id && conversationKey.startsWith(DRAFT_PREFIX)) {
            const persistedId = done.thread_id;
            setConversations((prev) => {
              const next = { ...prev };
              next[persistedId] = next[conversationKey] ?? [];
              delete next[conversationKey];
              return next;
            });
            if (activeKeyRef.current === conversationKey) {
              setActiveKey(persistedId);
            }
            void refreshThreads();
          }
        }
      }
    } catch {
      // finally의 dropped 처리
    } finally {
      patchConversation(conversationKey, (prev) => {
        if (prev[turnIndex]?.status !== "streaming") return prev;
        const next = [...prev];
        next[turnIndex] = { ...next[turnIndex], status: "dropped" };
        return next;
      });
      setSubmittingKeys((prev) => {
        const next = { ...prev };
        delete next[conversationKey];
        return next;
      });
    }
  }

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const text = question;
    setQuestion("");
    void submitQuestion(text, activeKey);
  }

  function handleNewConversation() {
    const key = newDraftKey();
    setConversations((prev) => ({ ...prev, [key]: [] }));
    setActiveKey(key);
    setRestoreError(null);
    setDrawerOpen(false);
    const input = document.getElementById("ask-question-input");
    input?.focus();
  }

  async function handleMarkerClick(part: AnchorPart) {
    if (!part.id) return;
    const base = `${workspacePath(workspaceId)}/ask`;

    if (part.kind === "wiki") {
      const supabase = createClient();
      const { data } = await supabase
        .from("wiki_pages")
        .select("slug")
        .eq("workspace_id", workspaceId)
        .eq("id", part.id)
        .single();
      if (data?.slug) {
        router.push(`${base}?slug=${encodeURIComponent(data.slug)}&tab=wiki`);
      }
      return;
    }

    router.push(`${base}?chunkId=${encodeURIComponent(part.id)}&tab=source`);
  }

  return (
    <section
      className="conversation relative flex h-full min-w-0"
      data-od-id="conversation-thread"
    >
      <ThreadDrawer
        open={drawerOpen}
        onOpenChange={setDrawerOpen}
        threads={threads}
        activeThreadId={activeThreadId}
        loading={listLoading}
        error={listError}
        onRetry={() => void refreshThreads()}
        onSelect={(threadId) => {
          void openThread(threadId);
          if (typeof window !== "undefined" && window.innerWidth < 1200) {
            setDrawerOpen(false);
          }
        }}
        onNew={handleNewConversation}
        onRename={(threadId, title) => {
          void renameAskThread(workspaceId, threadId, title).then((row) => {
            setThreads((prev) =>
              prev.map((item) => (item.id === row.id ? row : item)),
            );
          });
        }}
        onDelete={(threadId, title) => setDeleteTarget({ id: threadId, title })}
      />

      <div className="flex-1 flex flex-col min-w-0 h-full overflow-hidden">
        <header className="conversation-head">
          <div className="flex w-full items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <button
                type="button"
                className="icon-btn"
                aria-label={drawerOpen ? "대화 목록 닫기" : "대화 목록 열기"}
                aria-expanded={drawerOpen}
                onClick={() => setDrawerOpen(!drawerOpen)}
              >
                {drawerOpen ? (
                  <PanelLeftClose aria-hidden="true" size={18} />
                ) : (
                  <PanelLeftOpen aria-hidden="true" size={18} />
                )}
              </button>
              <h1>질문하기</h1>
            </div>
            <div
              className="flex items-center gap-2.5 rounded-lg border border-[var(--border)] bg-[var(--surface)]/60 px-2.5 py-1 text-[11px] text-[var(--muted)] shadow-2xs"
              aria-label="이중 인용 범례"
            >
              <span className="inline-flex items-center gap-1.5 font-medium">
                <span
                  className="cite source font-mono font-bold"
                  aria-hidden="true"
                >
                  1
                </span>
                <span>원문 소스</span>
              </span>
              <span className="text-[var(--border-strong)] opacity-40">·</span>
              <span className="inline-flex items-center gap-1.5 font-medium">
                <span className="cite font-mono font-bold" aria-hidden="true">
                  2
                </span>
                <span>위키 문서</span>
              </span>
            </div>
          </div>
        </header>
        <div className="thread" data-testid="ask-conversation">
          {restoreError === "deleted" ? (
            <article
              className="answer notice"
              role="alert"
              data-testid="thread-gone"
            >
              <p>삭제된 대화입니다.</p>
              <button
                type="button"
                className="button compact"
                onClick={handleNewConversation}
              >
                새 대화
              </button>
            </article>
          ) : null}
          {restoreError === "load_failed" ? (
            <article className="answer notice" role="alert">
              <p>이 대화를 볼 수 있는 권한이 없습니다.</p>
            </article>
          ) : null}
          {turns.length === 0 && restoreError === null ? (
            <div className="thread-empty">
              <b>{EMPTY_HEADING}</b>
              <span>{EMPTY_BODY}</span>
            </div>
          ) : turns.length > 0 ? (
            <p className="thread-meta">대화 · 원문과 위키 이중 인용</p>
          ) : null}

          {turns.map((turn, index) => (
            <Fragment key={index}>
              <article className="user" data-testid={`ask-turn-${index}`}>
                {turn.question}
              </article>

              {turn.missingChannelsNotice ? (
                <p
                  role="status"
                  data-testid="missing-channels-notice"
                  className="thread-meta"
                >
                  {MISSING_CHANNELS_NOTICE}
                </p>
              ) : null}

              {turn.status === "no-evidence" ? (
                <article
                  role="alert"
                  data-variant="warning"
                  data-testid="no-evidence-card"
                  className="answer notice"
                >
                  <p>{NO_EVIDENCE_MESSAGE}</p>
                </article>
              ) : turn.status === "error" ? (
                <article
                  role="alert"
                  data-variant="error"
                  data-testid="ask-error-card"
                  className="answer notice"
                >
                  <p>{GENERIC_ERROR_MESSAGE}</p>
                  <button
                    type="button"
                    className="button compact"
                    onClick={() =>
                      void submitQuestion(turn.question, activeKey)
                    }
                  >
                    재시도
                  </button>
                </article>
              ) : turn.status === "dropped" ? (
                <article
                  role="alert"
                  data-variant="dropped"
                  data-testid="stream-drop-card"
                  className="answer notice"
                >
                  <p>{STREAM_DROP_MESSAGE}</p>
                  <button
                    type="button"
                    className="button compact"
                    onClick={() =>
                      void submitQuestion(turn.question, activeKey)
                    }
                  >
                    재시도
                  </button>
                </article>
              ) : (
                <article className="answer" data-od-id="ai-answer">
                  <div className="answer-head">
                    <i className="dot" aria-hidden="true" />
                    <b>넥서스위키 AI 답변</b>
                    <span>
                      {turn.status === "streaming"
                        ? "생성 중"
                        : turn.persisted
                          ? "저장된 답변"
                          : "방금 생성됨"}
                    </span>
                  </div>
                  <div data-testid={`ask-turn-${index}-body`}>
                    <MarkdownAnswer
                      segments={turn.segments}
                      resolved={turn.status === "resolved"}
                      onMarkerClick={handleMarkerClick}
                    />
                  </div>
                </article>
              )}
            </Fragment>
          ))}
        </div>

        {templates.length > 0 ? (
          <div className="chips" role="group" aria-label="프롬프트 템플릿">
            {templates.map((template) => (
              <button
                key={template.id}
                type="button"
                onClick={() => setTemplateId(template.id)}
                aria-pressed={templateId === template.id}
                className="chip"
              >
                {template.name}
              </button>
            ))}
          </div>
        ) : null}

        <form
          onSubmit={handleSubmit}
          className="composer"
          data-od-id="follow-up-composer"
        >
          <label htmlFor="ask-question-input" className="sr-only">
            질문
          </label>
          <div className="compose-inner">
            <input
              id="ask-question-input"
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="이어서 추가 질문을 입력하세요"
              className="flex-1 min-w-0 bg-transparent border-0 outline-none focus:outline-none focus:ring-0 focus-visible:outline-none focus-visible:ring-0 shadow-none text-xs text-[var(--fg)] placeholder:text-[var(--muted)]"
            />
            <button
              type="submit"
              className="send"
              aria-label="질문하기"
              disabled={question.trim().length === 0 || submitting}
            >
              <span aria-hidden="true">↑</span>
            </button>
          </div>
        </form>
      </div>

      <Dialog.Root
        open={deleteTarget !== null}
        onOpenChange={(open) => {
          if (!open) setDeleteTarget(null);
        }}
      >
        <Dialog.Portal>
          <Dialog.Overlay className="modal-backdrop fixed inset-0" />
          <Dialog.Content className="modal fixed top-1/2 left-1/2 z-50 w-[min(540px,calc(100vw-32px))] -translate-x-1/2 -translate-y-1/2">
            <div className="modal-head">
              <Dialog.Title>대화 삭제</Dialog.Title>
            </div>
            <Dialog.Description className="text-[13px] text-[var(--muted)]">
              {deleteTarget
                ? `삭제: '${deleteTarget.title}' 대화를 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.`
                : ""}
            </Dialog.Description>
            <div className="modal-foot">
              <Dialog.Close asChild>
                <button type="button" className="button">
                  취소
                </button>
              </Dialog.Close>
              <button
                type="button"
                className="button danger"
                onClick={() => {
                  if (!deleteTarget) return;
                  const target = deleteTarget;
                  void deleteAskThread(workspaceId, target.id).then(() => {
                    setThreads((prev) =>
                      prev.filter((row) => row.id !== target.id),
                    );
                    if (activeKey === target.id) {
                      handleNewConversation();
                    }
                    setDeleteTarget(null);
                  });
                }}
              >
                삭제
              </button>
            </div>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </section>
  );
}

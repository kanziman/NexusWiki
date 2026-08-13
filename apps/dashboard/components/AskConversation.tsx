"use client";

import { useEffect, useState } from "react";

import { CitationMarker } from "@/components/CitationMarker";
import { CitationSidePanel } from "@/components/CitationSidePanel";
import {
  splitTextWithAnchors,
  type AnchorPart,
  type ResolvedAnchor,
  type TextPart,
} from "@/lib/citation-anchors";
import { requireEnv } from "@/lib/env";
import { parseSseStream } from "@/lib/sse";
import { createClient } from "@/lib/supabase/client";

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
};

// UI-SPEC Copywriting Contract(Ask UI(UI-04)) — 문구를 한 글자도 바꾸지 않는다.
const EMPTY_HEADING = "무엇이든 물어보세요";
const EMPTY_BODY = "워크스페이스에 등록된 소스와 위키에서 답을 찾아드립니다.";
const NO_EVIDENCE_MESSAGE = "근거를 찾지 못했습니다."; // CITE-04/D-11 verbatim
const MISSING_CHANNELS_NOTICE =
  "일부 검색 채널을 사용할 수 없어 답변이 불완전할 수 있습니다.";
const STREAM_DROP_MESSAGE = "연결이 끊어졌습니다. 다시 시도해주세요.";
const GENERIC_ERROR_MESSAGE =
  "질문에 답하지 못했습니다. 잠시 후 다시 시도해주세요.";
const REQUESTED_K = 8; // RetrievalService.DEFAULT_RETRIEVAL_POLICY.requested_k와 일치

/**
 * `/ask` SSE 엔드포인트가 non-2xx로 응답할 때(401/402/403/500 등)의 본문은
 * `lib/api-client.ts`의 `ApiError`와 같은 `{ detail: string, ... }` 형태를
 * 따른다는 보장이 없으므로 최선 노력으로만 파싱한다 — 파싱에 실패해도 예외를
 * 밖으로 던지지 않고 고정 토큰으로 대체한다(threat T-06-13과 동일한 방어).
 */
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

/**
 * Ask UI 대화 상태 기계 — `meta -> delta* -> citations -> done` 이벤트 순서를
 * 그대로 소비한다 (05-CONTEXT.md D-01~D-03, 06-CONTEXT.md D-09~D-11).
 *
 * 관련 태스크: 06-06-PLAN.md Task 2
 * 설계 근거: apps/api/src/api/services/ask.py (SSE 페이로드의 정확한 형태),
 *            06-UI-SPEC.md Copywriting Contract "Ask UI (UI-04)"
 *
 * ⚠️ 마커는 `citations` 이벤트가 도착하기 전까지 절대 실제 링크로 렌더되지 않는다
 * (T-06-18) — 스트리밍 중에는 `splitTextWithAnchors(text)`(해소 맵 없음)만 써서
 * 위조 여부와 무관하게 전부 동일한 비활성 placeholder로 렌더한다. `citations`
 * 프레임이 도착해야만 `splitTextWithAnchors(text, resolved)`로 다시 나눠 실제
 * 발급된 앵커만 클릭 가능한 마커로 승격한다.
 */
export function AskConversation({ workspaceId }: AskConversationProps) {
  const [templates, setTemplates] = useState<PromptTemplate[]>([]);
  const [templateId, setTemplateId] = useState<string | undefined>(undefined);
  const [question, setQuestion] = useState("");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [panelPart, setPanelPart] = useState<AnchorPart | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadTemplates() {
      const supabase = createClient();
      // API-02: RLS(prompt_templates_select_global_or_member)가 이미 전역/멤버
      // 워크스페이스로 가시 범위를 좁혀 두므로 여기서는 그대로 읽기만 한다.
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

  async function submitQuestion(text: string) {
    const trimmed = text.trim();
    if (trimmed.length === 0 || submitting) return;

    // 버튼이 submitting 동안 비활성화되므로 동시에 두 번째 호출이 들어올 수
    // 없다 — turns.length를 이 시점의 새 턴 인덱스로 안전하게 캡처할 수 있다.
    const turnIndex = turns.length;
    setSubmitting(true);
    setTurns((prev) => [
      ...prev,
      {
        question: trimmed,
        segments: [],
        status: "streaming",
        missingChannelsNotice: false,
      },
    ]);

    function patchTurn(patch: Partial<Turn>) {
      setTurns((prev) => {
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

      // apiFetch()를 쓰지 않는다 — 그 헬퍼는 JSON 응답을 가정하지만 이 엔드포인트는
      // SSE 스트림을 반환한다(06-04-SUMMARY.md). 인증 헤더 부착 방식만 apiFetch와
      // 동일하게 맞춘다(요청마다 새 세션 토큰을 읽는다).
      // 06-REVIEW.md WR-05: unset이면 이전에는 이 문자열이 그대로
      // "undefined/..."로 나갔다 — requireEnv로 fail-fast(CLAUDE.md 규칙)한다.
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
          }),
        },
      );

      // 06-REVIEW.md WR-02: 응답이 SSE가 아닌 JSON 에러 본문(401/402/403/500 등)일
      // 수 있다 — response.ok를 먼저 확인하지 않으면 parseSseStream이 프레임
      // 경계를 하나도 못 찾고 조용히 0개 이벤트만 내보내, 아래 finally의
      // "streaming으로 남아있으면 dropped" 규칙이 실제 서버 에러를 일반
      // "연결이 끊어졌습니다" 재시도 안내로 뭉개버린다. 여기서 먼저 걸러서
      // 명시적인 error 상태로 분기한다.
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
          // RTV-09 meta.missing_channels — ask.py는 아직 이 필드를 보내지 않을
          // 수 있다(05-06-PLAN.md 문서화된 가정). 있고 비어있지 않을 때만 방어적으로
          // 렌더한다 — 없으면 그냥 조용히 아무 일도 하지 않는다(안전한 저하).
          if (meta.missing_channels && meta.missing_channels.length > 0) {
            patchTurn({ missingChannelsNotice: true });
          }
        } else if (frame.event === "delta") {
          const delta = frame.data as { text: string };
          accumulatedText += delta.text;
          // 해소 맵 없이 — 아직 발급 여부를 모르므로 전부 비활성 placeholder다.
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
        }
        // "done"은 상태를 바꾸지 않는다 — 렌더 전환은 이미 citations 프레임에서
        // 끝났다. done은 스트림이 정상 종료됐다는 신호일 뿐이다.
      }
    } catch {
      // 네트워크 실패 등 — 아래 finally의 "streaming으로 남아있으면 dropped"
      // 규칙이 이 경우도 함께 처리한다.
    } finally {
      setTurns((prev) => {
        if (prev[turnIndex]?.status !== "streaming") return prev;
        // citations/error/no-evidence 프레임이 끝내 도착하지 않고 스트림이
        // 끝났다 — done 이벤트를 보지 못한 것과 동일한 증상이다.
        const next = [...prev];
        next[turnIndex] = { ...next[turnIndex], status: "dropped" };
        return next;
      });
      setSubmitting(false);
    }
  }

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const text = question;
    setQuestion("");
    void submitQuestion(text);
  }

  function handleMarkerClick(part: AnchorPart) {
    setPanelPart(part);
  }

  return (
    <div className="flex flex-col gap-lg">
      {turns.length === 0 ? (
        <div className="flex flex-col items-center gap-xs py-section text-center">
          <p className="text-ink" style={{ font: "var(--font-display-xl)" }}>
            {EMPTY_HEADING}
          </p>
          <p className="text-muted" style={{ font: "var(--font-body-md)" }}>
            {EMPTY_BODY}
          </p>
        </div>
      ) : null}

      <div className="flex flex-col gap-lg" data-testid="ask-conversation">
        {turns.map((turn, index) => (
          <div
            key={index}
            className="flex flex-col gap-xs"
            data-testid={`ask-turn-${index}`}
          >
            <p className="text-ink" style={{ font: "var(--font-title-md)" }}>
              {turn.question}
            </p>

            {turn.missingChannelsNotice ? (
              <p
                role="status"
                data-testid="missing-channels-notice"
                className="text-muted"
                style={{ font: "var(--font-caption)", fontWeight: 600 }}
              >
                {MISSING_CHANNELS_NOTICE}
              </p>
            ) : null}

            {turn.status === "no-evidence" ? (
              // CITE-04/D-11: 채팅 버블과 시각적으로 구분되는 경고 카드 — 절대
              // 일반 답변 버블 스타일로 렌더하지 않는다.
              <div
                role="alert"
                data-variant="warning"
                data-testid="no-evidence-card"
                className="rounded-md border border-primary-error-text bg-surface-soft p-base"
              >
                <p
                  className="text-primary-error-text"
                  style={{ font: "var(--font-body-md)" }}
                >
                  {NO_EVIDENCE_MESSAGE}
                </p>
              </div>
            ) : turn.status === "error" ? (
              <div
                role="alert"
                data-variant="error"
                data-testid="ask-error-card"
                className="flex flex-col gap-xs rounded-md border border-primary-error-text bg-canvas p-base"
              >
                <p
                  className="text-primary-error-text"
                  style={{ font: "var(--font-body-md)" }}
                >
                  {GENERIC_ERROR_MESSAGE}
                </p>
                <button
                  type="button"
                  onClick={() => void submitQuestion(turn.question)}
                  className="self-start rounded-sm border border-primary-error-text px-base py-sm text-primary-error-text"
                  style={{ font: "var(--font-caption)", fontWeight: 600 }}
                >
                  재시도
                </button>
              </div>
            ) : turn.status === "dropped" ? (
              <div
                role="alert"
                data-variant="dropped"
                data-testid="stream-drop-card"
                className="flex flex-col gap-xs rounded-md border border-primary-error-text bg-canvas p-base"
              >
                <p
                  className="text-primary-error-text"
                  style={{ font: "var(--font-body-md)" }}
                >
                  {STREAM_DROP_MESSAGE}
                </p>
                <button
                  type="button"
                  onClick={() => void submitQuestion(turn.question)}
                  className="self-start rounded-sm border border-primary-error-text px-base py-sm text-primary-error-text"
                  style={{ font: "var(--font-caption)", fontWeight: 600 }}
                >
                  재시도
                </button>
              </div>
            ) : (
              <p
                className="text-ink"
                style={{ font: "var(--font-body-md)" }}
                data-testid={`ask-turn-${index}-body`}
              >
                {renderSegments(
                  turn.segments,
                  turn.status === "resolved",
                  handleMarkerClick,
                )}
              </p>
            )}
          </div>
        ))}
      </div>

      {templates.length > 0 ? (
        <div className="flex gap-xs" role="group" aria-label="프롬프트 템플릿">
          {templates.map((template) => (
            <button
              key={template.id}
              type="button"
              onClick={() => setTemplateId(template.id)}
              aria-pressed={templateId === template.id}
              className={`rounded-full border px-base py-xs ${
                templateId === template.id
                  ? "border-primary text-primary"
                  : "border-hairline text-muted"
              }`}
              style={{ font: "var(--font-caption)", fontWeight: 600 }}
            >
              {template.name}
            </button>
          ))}
        </div>
      ) : null}

      {/* UI-SPEC Primary Visual Anchor(Ask UI): 입력창이 이 화면의 1차 시각적
          초점이다 — 전체 폭, 강조 테두리, accent 색 전송 버튼이 붙는다. */}
      <form onSubmit={handleSubmit} className="flex gap-sm">
        <label htmlFor="ask-question-input" className="sr-only">
          질문
        </label>
        <input
          id="ask-question-input"
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          className="h-12 flex-1 rounded-sm border border-border-strong bg-canvas px-base text-ink outline-none focus:border-2 focus:border-ink"
          style={{ font: "var(--font-body-md)" }}
        />
        <button
          type="submit"
          disabled={question.trim().length === 0 || submitting}
          className="h-12 rounded-sm bg-primary px-lg text-on-primary transition-colors active:bg-primary-active disabled:cursor-not-allowed disabled:bg-primary-disabled"
          style={{ font: "var(--font-button-md)", fontWeight: 600 }}
        >
          질문하기
        </button>
      </form>

      <CitationSidePanel
        part={panelPart}
        onClose={() => setPanelPart(null)}
        workspaceId={workspaceId}
      />
    </div>
  );
}

function renderSegments(
  segments: (TextPart | AnchorPart)[],
  resolved: boolean,
  onMarkerClick: (part: AnchorPart) => void,
) {
  let anchorIndex = 0;
  return segments.map((part, i) => {
    if (part.type === "text") {
      return <span key={i}>{part.value}</span>;
    }
    const index = anchorIndex;
    anchorIndex += 1;
    return (
      <CitationMarker
        key={i}
        part={part}
        index={index}
        resolved={resolved}
        onClick={onMarkerClick}
      />
    );
  });
}

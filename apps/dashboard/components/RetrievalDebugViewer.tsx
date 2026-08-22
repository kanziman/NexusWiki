"use client";

import { useMemo, useState } from "react";

import { ApiError, apiFetch } from "@/lib/api-client";
import { createClient } from "@/lib/supabase/client";

import styles from "./RetrievalDebugViewer.module.css";

export const RETRIEVAL_CHANNELS = [
  "wiki_vector",
  "source_vector",
  "wiki_lexical",
  "source_lexical",
] as const;

type RetrievalChannel = (typeof RETRIEVAL_CHANNELS)[number];

type RetrievalEvidence = {
  id: string;
  kind: string;
  document_id: string;
  channels: string[];
  contributions: Record<string, number>;
  metadata: Record<string, unknown>;
};

type ChannelMeta = {
  status?: string;
  returned?: number;
  elapsed_ms?: number;
  raw_hit_ids?: string[];
  reason?: string;
};

export type RetrievalResponse = {
  evidence: RetrievalEvidence[];
  meta: {
    policy_version?: string;
    elapsed_ms?: number;
    requested_k?: number;
    returned?: number;
    underfill?: boolean;
    [key: string]: unknown;
  };
};

type RetrievalDebugViewerProps = { workspaceId: string };

const CHANNEL_LABELS: Record<RetrievalChannel, string> = {
  wiki_vector: "위키 벡터",
  source_vector: "원문 벡터",
  wiki_lexical: "위키 어휘",
  source_lexical: "원문 어휘",
};

const META_SUMMARY_KEYS = new Set([
  "policy_version",
  "elapsed_ms",
  "requested_k",
  "returned",
  "underfill",
]);

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function channelMeta(
  response: RetrievalResponse,
  channel: RetrievalChannel,
): ChannelMeta {
  const value = response.meta[channel];
  return isRecord(value) ? (value as ChannelMeta) : {};
}

function totalContribution(evidence: RetrievalEvidence): number {
  return Object.values(evidence.contributions).reduce(
    (total, contribution) => total + contribution,
    0,
  );
}

function formatNumber(value: number | undefined, digits = 3): string {
  return typeof value === "number" ? value.toFixed(digits) : "—";
}

function formatMetadata(metadata: Record<string, unknown>): string {
  const entries = Object.entries(metadata).slice(0, 4);
  if (entries.length === 0) return "metadata 없음";
  return entries
    .map(([key, value]) => {
      const rendered =
        typeof value === "string" || typeof value === "number"
          ? String(value)
          : JSON.stringify(value);
      return `${key}: ${rendered}`;
    })
    .join(" · ");
}

type ContentState = {
  status: "loading" | "loaded" | "error";
  text?: string;
};

// wiki_vector는 wiki_embeddings(청크 단위), wiki_lexical은 wiki_pages(페이지
// 단위, search_wiki_lexical이 청크 없이 페이지 id를 그대로 evidence.id로 쓴다),
// source_vector·source_lexical은 둘 다 source_chunks — apps/api/src/api/services/
// retrieval.py의 _wiki_vector_hit·_wiki_lexical_hit·_source_hit 매핑과 일치시킨다.
function resolveContentTarget(
  evidence: RetrievalEvidence,
): { table: string; column: string } | null {
  if (evidence.kind === "source")
    return { table: "source_chunks", column: "content" };
  if (evidence.kind === "wiki") {
    if (evidence.channels.includes("wiki_vector")) {
      return { table: "wiki_embeddings", column: "chunk_content" };
    }
    if (evidence.channels.includes("wiki_lexical")) {
      return { table: "wiki_pages", column: "content" };
    }
  }
  return null;
}

function unknownChannels(response: RetrievalResponse): string[] {
  const found = new Set<string>();

  for (const key of Object.keys(response.meta)) {
    if (
      !META_SUMMARY_KEYS.has(key) &&
      !RETRIEVAL_CHANNELS.includes(key as RetrievalChannel)
    ) {
      found.add(key);
    }
  }
  for (const evidence of response.evidence) {
    for (const key of [
      ...evidence.channels,
      ...Object.keys(evidence.contributions),
    ]) {
      if (!RETRIEVAL_CHANNELS.includes(key as RetrievalChannel)) found.add(key);
    }
  }

  return [...found].sort();
}

// 구현 추적: openspec/changes/retrieval-debug-viewer
export function RetrievalDebugViewer({
  workspaceId,
}: RetrievalDebugViewerProps) {
  const [query, setQuery] = useState("");
  const [requestedK, setRequestedK] = useState(8);
  const [response, setResponse] = useState<RetrievalResponse | null>(null);
  const [errorDetail, setErrorDetail] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [contentState, setContentState] = useState<
    Record<string, ContentState>
  >({});
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());

  const fusedEvidence = useMemo(
    () =>
      response
        ? [...response.evidence].sort(
            (left, right) => totalContribution(right) - totalContribution(left),
          )
        : [],
    [response],
  );

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = query.trim();
    if (trimmed.length === 0) {
      setErrorDetail("질의를 입력해 주세요.");
      return;
    }

    setSubmitting(true);
    setErrorDetail(null);
    setContentState({});
    setExpandedIds(new Set());
    try {
      const nextResponse = await apiFetch<RetrievalResponse>(
        `/workspaces/${encodeURIComponent(workspaceId)}/retrieval`,
        {
          method: "POST",
          body: { query: trimmed, requested_k: requestedK },
        },
      );
      setResponse(nextResponse);
    } catch (error) {
      setResponse(null);
      setErrorDetail(
        error instanceof ApiError ? error.detail : "unknown_error",
      );
    } finally {
      setSubmitting(false);
    }
  }

  const evidenceById = new Map(
    response?.evidence.map((evidence) => [evidence.id, evidence]),
  );
  const extraChannels = response ? unknownChannels(response) : [];

  async function loadContent(evidence: RetrievalEvidence) {
    const target = resolveContentTarget(evidence);
    if (!target) {
      setContentState((prev) => ({
        ...prev,
        [evidence.id]: {
          status: "error",
          text: "조회 대상 테이블을 알 수 없습니다.",
        },
      }));
      return;
    }
    setContentState((prev) => ({
      ...prev,
      [evidence.id]: { status: "loading" },
    }));
    const supabase = createClient();
    const { data, error } = await supabase
      .from(target.table)
      .select(target.column)
      .eq("id", evidence.id)
      .single();
    if (error || !data) {
      setContentState((prev) => ({
        ...prev,
        [evidence.id]: { status: "error", text: error?.message ?? "not_found" },
      }));
      return;
    }
    const raw = (data as unknown as Record<string, unknown>)[target.column];
    setContentState((prev) => ({
      ...prev,
      [evidence.id]: {
        status: "loaded",
        text: typeof raw === "string" ? raw : "",
      },
    }));
  }

  function toggleContent(evidence: RetrievalEvidence) {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(evidence.id)) {
        next.delete(evidence.id);
      } else {
        next.add(evidence.id);
        if (!contentState[evidence.id]) void loadContent(evidence);
      }
      return next;
    });
  }

  return (
    <div className={styles.viewer}>
      <header className={styles.header}>
        <div>
          <h1>검색 파이프라인 디버그</h1>
          <p>
            실제 워크스페이스 검색의 채널별 원시 순서와 RRF 기여도를 비교합니다.
          </p>
        </div>
        <span className={styles.developmentBadge}>개발 환경 전용</span>
      </header>

      <form className={styles.queryForm} onSubmit={handleSubmit}>
        <label className={styles.queryField}>
          <span>질의</span>
          <input
            className="nw-input nw-focus-ring"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="검색 파이프라인에 보낼 질의"
            disabled={submitting}
          />
        </label>
        <label className={styles.countField}>
          <span>결과 수</span>
          <select
            className="nw-input nw-focus-ring"
            value={requestedK}
            onChange={(event) => setRequestedK(Number(event.target.value))}
            disabled={submitting}
          >
            {Array.from({ length: 8 }, (_, index) => index + 1).map((count) => (
              <option key={count} value={count}>
                {count}
              </option>
            ))}
          </select>
        </label>
        <button
          className="nw-action nw-focus-ring"
          type="submit"
          disabled={submitting}
        >
          {submitting ? "조회 중…" : "검색 실행"}
        </button>
      </form>

      {errorDetail ? (
        <div className={styles.error} role="alert">
          <strong>조회하지 못했습니다.</strong>
          <code>{errorDetail}</code>
        </div>
      ) : null}

      {response ? (
        <div className={styles.results} aria-live="polite">
          <section aria-labelledby="retrieval-summary-heading">
            <div className={styles.sectionHeading}>
              <div>
                <h2 id="retrieval-summary-heading">실행 요약</h2>
                <p>정책과 각 검색 채널의 실행 상태입니다.</p>
              </div>
              <dl className={styles.overallSummary}>
                <div>
                  <dt>정책</dt>
                  <dd>{response.meta.policy_version ?? "—"}</dd>
                </div>
                <div>
                  <dt>총 소요</dt>
                  <dd>{formatNumber(response.meta.elapsed_ms)} ms</dd>
                </div>
              </dl>
            </div>

            <div className={styles.channelSummary}>
              {RETRIEVAL_CHANNELS.map((channel) => {
                const meta = channelMeta(response, channel);
                return (
                  <dl key={channel}>
                    <div className={styles.summaryTitle}>
                      <dt>{CHANNEL_LABELS[channel]}</dt>
                      <dd data-status={meta.status ?? "unknown"}>
                        {meta.status ?? "unknown"}
                      </dd>
                    </div>
                    <div>
                      <dt>결과</dt>
                      <dd>{meta.returned ?? 0}</dd>
                    </div>
                    <div>
                      <dt>소요</dt>
                      <dd>{formatNumber(meta.elapsed_ms)} ms</dd>
                    </div>
                  </dl>
                );
              })}
            </div>

            {extraChannels.length > 0 ? (
              <p className={styles.unknownNotice} role="status">
                알 수 없는 채널: <code>{extraChannels.join(", ")}</code>
              </p>
            ) : null}
          </section>

          <section aria-labelledby="raw-results-heading">
            <div className={styles.sectionHeading}>
              <div>
                <h2 id="raw-results-heading">채널별 원시 결과</h2>
                <p>서버의 raw_hit_ids 순서를 그대로 표시합니다.</p>
              </div>
            </div>
            <div className={styles.rawChannels}>
              {RETRIEVAL_CHANNELS.map((channel) => {
                const meta = channelMeta(response, channel);
                const hitIds = Array.isArray(meta.raw_hit_ids)
                  ? meta.raw_hit_ids
                  : response.evidence
                      .filter((evidence) => evidence.channels.includes(channel))
                      .map((evidence) => evidence.id);
                const isUnavailable = meta.status !== "ok";

                return (
                  <article className={styles.channelPanel} key={channel}>
                    <header>
                      <div>
                        <h3>{CHANNEL_LABELS[channel]}</h3>
                        <code>{channel}</code>
                      </div>
                      <span data-status={meta.status ?? "unknown"}>
                        {meta.status ?? "unknown"}
                      </span>
                    </header>

                    {isUnavailable || hitIds.length === 0 ? (
                      <div className={styles.channelEmpty}>
                        <strong>
                          {isUnavailable
                            ? "채널을 사용할 수 없음"
                            : "반환 결과 0건"}
                        </strong>
                        <span>
                          {meta.reason ?? `status: ${meta.status ?? "unknown"}`}
                        </span>
                      </div>
                    ) : (
                      <ol className={styles.hitList}>
                        {hitIds.map((hitId) => {
                          const evidence = evidenceById.get(hitId);
                          return (
                            <li key={hitId}>
                              <span className={styles.rank} aria-label="순위">
                                {hitIds.indexOf(hitId) + 1}
                              </span>
                              <div>
                                <code>{hitId}</code>
                                {evidence ? (
                                  <>
                                    <span>
                                      {evidence.kind} · {evidence.document_id}
                                    </span>
                                    <small>
                                      {formatMetadata(evidence.metadata)}
                                    </small>
                                    <button
                                      type="button"
                                      className={styles.contentToggle}
                                      onClick={() => toggleContent(evidence)}
                                    >
                                      {expandedIds.has(evidence.id)
                                        ? "내용 숨기기"
                                        : "내용 보기"}
                                    </button>
                                    {expandedIds.has(evidence.id) ? (
                                      <div className={styles.contentPreview}>
                                        {contentState[evidence.id]?.status ===
                                        "loading" ? (
                                          <span>불러오는 중…</span>
                                        ) : contentState[evidence.id]
                                            ?.status === "error" ? (
                                          <span role="alert">
                                            조회 실패:{" "}
                                            {contentState[evidence.id]?.text}
                                          </span>
                                        ) : (
                                          <pre>
                                            {contentState[evidence.id]?.text ||
                                              "(빈 내용)"}
                                          </pre>
                                        )}
                                      </div>
                                    ) : null}
                                  </>
                                ) : (
                                  <small>융합 상위 결과 밖의 evidence</small>
                                )}
                              </div>
                            </li>
                          );
                        })}
                      </ol>
                    )}
                  </article>
                );
              })}
            </div>
          </section>

          <section aria-labelledby="fused-ranking-heading">
            <div className={styles.sectionHeading}>
              <div>
                <h2 id="fused-ranking-heading">RRF 융합 랭킹</h2>
                <p>채널별 contribution 합계의 내림차순입니다.</p>
              </div>
            </div>
            <div className={styles.tableWrap}>
              <table>
                <thead>
                  <tr>
                    <th scope="col">순위</th>
                    <th scope="col">문서</th>
                    <th scope="col">참여 채널</th>
                    <th scope="col">채널별 기여</th>
                    <th scope="col">총점</th>
                  </tr>
                </thead>
                <tbody>
                  {fusedEvidence.map((evidence, index) => (
                    <tr key={evidence.id}>
                      <td>{index + 1}</td>
                      <td>
                        <strong>{evidence.document_id}</strong>
                        <code>{evidence.id}</code>
                      </td>
                      <td>
                        <div className={styles.channelTags}>
                          {evidence.channels.map((channel) => (
                            <span key={channel}>
                              {RETRIEVAL_CHANNELS.includes(
                                channel as RetrievalChannel,
                              )
                                ? channel
                                : `알 수 없는 채널 (${channel})`}
                            </span>
                          ))}
                        </div>
                      </td>
                      <td>
                        <dl className={styles.contributions}>
                          {Object.entries(evidence.contributions).map(
                            ([channel, contribution]) => (
                              <div key={channel}>
                                <dt>{channel}</dt>
                                <dd>{formatNumber(contribution, 6)}</dd>
                              </div>
                            ),
                          )}
                        </dl>
                      </td>
                      <td className={styles.totalScore}>
                        {formatNumber(totalContribution(evidence), 6)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {fusedEvidence.length === 0 ? (
                <p className={styles.fusedEmpty}>융합 evidence가 없습니다.</p>
              ) : null}
            </div>
          </section>
        </div>
      ) : (
        <div className={styles.initialState}>
          <strong>아직 실행한 질의가 없습니다.</strong>
          <span>질의와 결과 수를 정한 뒤 검색을 실행하세요.</span>
        </div>
      )}
    </div>
  );
}

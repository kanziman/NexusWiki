"use client";

import {
  ArrowLeft,
  Check,
  Loader2,
  MonitorPlay,
  TriangleAlert,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

import { CreditLimitModal } from "@/components/CreditLimitModal";
import type { YoutubeChannel } from "@/components/YoutubeChannelSearch";
import { ApiError, apiFetch } from "@/lib/api-client";

export type YoutubeVideo = {
  video_id: string;
  title: string;
  published_at: string | null;
  duration_seconds: number | null;
  thumbnail_url: string | null;
  has_captions: boolean | null;
  view_count: number | null;
  like_count: number | null;
};

type ChannelVideosResponse = {
  videos: YoutubeVideo[];
  next_page_token: string | null;
};

/** 서버가 영상마다 돌려주는 결과 한 줄 (`sources.py`의 일괄 등록 응답). */
type IngestResult = {
  video_id: string;
  status: "registered" | "already_collected" | "failed";
  raw_source_id?: string;
  job_id?: string;
  reason?: string;
};

export type YoutubeVideoListProps = {
  workspaceId: string;
  channel: YoutubeChannel;
  onBack: () => void;
};

// ⚠️ 문구는 detail 토큰별로 고른다 — 서버는 짧은 기계 판독 토큰만 내려주고 문장은 여기
//    산다 (`YoutubeChannelSearch`와 같은 규약). 문장으로 분기하면 API 배포가 UI 문구를
//    인질로 잡는다.
const CHANNEL_GONE_MESSAGE =
  "이 채널을 더 이상 찾을 수 없습니다. 검색으로 돌아가 다른 채널을 골라 주세요.";
const QUOTA_MESSAGE =
  "오늘 사용할 수 있는 YouTube 조회 횟수를 모두 썼습니다. 내일 다시 시도해 주세요.";
const UNAVAILABLE_MESSAGE =
  "YouTube에 연결하지 못했습니다. 잠시 후 다시 시도해 주세요.";
const FORBIDDEN_MESSAGE = "이 워크스페이스에서 수집할 권한이 없습니다.";
const GENERIC_MESSAGE = "영상 목록을 불러오지 못했습니다.";

const BATCH_FORBIDDEN_MESSAGE = "이 워크스페이스에 수집할 권한이 없습니다.";
const BATCH_GENERIC_MESSAGE =
  "일괄 수집에 실패했습니다. 잠시 후 다시 시도해 주세요.";

// 영상별 결과 문구. `reason` 토큰이 늘어나면 여기 한 줄을 더한다.
const REASON_MESSAGES: Record<string, string> = {
  budget_exceeded: "이번 달 크레딧을 모두 소진해 수집하지 못했습니다.",
  bad_video_id: "영상 정보를 읽을 수 없어 건너뛰었습니다.",
  internal: "서버 오류로 수집하지 못했습니다.",
};
const UNKNOWN_REASON_MESSAGE = "수집하지 못했습니다.";

function listMessageFor(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.detail === "youtube_channel_not_found")
      return CHANNEL_GONE_MESSAGE;
    if (error.detail === "youtube_quota_exceeded") return QUOTA_MESSAGE;
    if (error.detail === "youtube_unavailable") return UNAVAILABLE_MESSAGE;
    if (error.status === 403) return FORBIDDEN_MESSAGE;
  }
  return GENERIC_MESSAGE;
}

export function resultLabel(result: IngestResult): string {
  if (result.status === "registered") return "수집 시작됨";
  // ⚠️ "이미 수집됨"은 실패가 아니다. 실패 문구로 뭉개면 사용자는 무엇을 고쳐야
  //    하는지 모르는 채 같은 영상을 계속 다시 고른다.
  if (result.status === "already_collected") return "이미 수집한 영상입니다";
  return REASON_MESSAGES[result.reason ?? ""] ?? UNKNOWN_REASON_MESSAGE;
}

export function formatDuration(seconds: number | null): string {
  // 길이를 모르는 것과 0초를 구분한다 — 서버가 `null`을 보내는 이유가 그것이다.
  if (seconds === null || seconds < 0) return "길이 정보 없음";
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const rest = seconds % 60;
  const pad = (value: number) => String(value).padStart(2, "0");
  return hours > 0
    ? `${hours}:${pad(minutes)}:${pad(rest)}`
    : `${minutes}:${pad(rest)}`;
}

export function formatCount(value: number | null | undefined): string {
  if (value === null || value === undefined || value < 0) return "";
  return value.toLocaleString("ko-KR");
}

export function formatPublishedAt(value: string | null): string {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleDateString("ko-KR", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

export function summarize(results: IngestResult[]): string {
  const registered = results.filter((r) => r.status === "registered").length;
  const already = results.filter(
    (r) => r.status === "already_collected",
  ).length;
  const failed = results.filter((r) => r.status === "failed").length;
  // ⚠️ 셋을 하나로 합치지 않는다. "3건 처리됨"은 등록된 것도 실패한 것도 같은 숫자에
  //    묻어버려, 사용자가 다시 눌러야 할 대상이 무엇인지 사라진다.
  const parts = [`${registered}건 수집 시작`];
  if (already > 0) parts.push(`${already}건 이미 수집됨`);
  if (failed > 0) parts.push(`${failed}건 실패`);
  return parts.join(" · ");
}

export function YoutubeVideoList({
  workspaceId,
  channel,
  onBack,
}: YoutubeVideoListProps) {
  const [videos, setVideos] = useState<YoutubeVideo[]>([]);
  const [nextPageToken, setNextPageToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [ingesting, setIngesting] = useState(false);
  const [results, setResults] = useState<Record<string, IngestResult>>({});
  const [batchError, setBatchError] = useState<string | null>(null);
  const [summary, setSummary] = useState<string | null>(null);
  const [creditLimitOpen, setCreditLimitOpen] = useState(false);

  const fetchPage = useCallback(
    async (pageToken: string | null) => {
      const params = new URLSearchParams();
      if (pageToken) params.set("page_token", pageToken);
      const query = params.toString();
      return apiFetch<ChannelVideosResponse>(
        `/workspaces/${workspaceId}/youtube/channels/${channel.channel_id}/videos${
          query ? `?${query}` : ""
        }`,
      );
    },
    [workspaceId, channel.channel_id],
  );

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    // ⚠️ 채널을 바꿀 때 이전 채널의 영상·선택·결과를 함께 비운다. 남겨두면 새 채널의
    //    목록에 이전 채널의 "수집됨" 배지가 섞여 보이고, 더 나쁘게는 보이지 않는
    //    이전 채널 영상이 선택된 채로 일괄 수집에 실려 나간다.
    setVideos([]);
    setNextPageToken(null);
    setSelected(new Set());
    setResults({});
    setSummary(null);
    setBatchError(null);

    fetchPage(null)
      .then((result) => {
        if (cancelled) return;
        setVideos(result.videos);
        setNextPageToken(result.next_page_token);
      })
      .catch((caught) => {
        if (cancelled) return;
        setError(listMessageFor(caught));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [fetchPage]);

  // 이미 결과가 나온 영상은 다시 고를 수 없다 — 같은 요청을 반복하게 두면 "이미
  // 수집됨"만 쌓인다.
  const selectableIds = useMemo(
    () => videos.map((v) => v.video_id).filter((id) => !results[id]),
    [videos, results],
  );
  const allSelected =
    selectableIds.length > 0 && selectableIds.every((id) => selected.has(id));

  function toggle(videoId: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(videoId)) next.delete(videoId);
      else next.add(videoId);
      return next;
    });
  }

  function toggleAll() {
    setSelected(allSelected ? new Set() : new Set(selectableIds));
  }

  async function handleLoadMore() {
    if (!nextPageToken || loadingMore) return;
    setLoadingMore(true);
    setError(null);
    try {
      const result = await fetchPage(nextPageToken);
      setVideos((prev) => [...prev, ...result.videos]);
      setNextPageToken(result.next_page_token);
    } catch (caught) {
      // 더 보기 실패는 이미 받은 목록과 선택을 지우지 않는다.
      setError(listMessageFor(caught));
    } finally {
      setLoadingMore(false);
    }
  }

  async function handleIngestSelected() {
    if (selected.size === 0 || ingesting) return;
    // 선택 순서가 아니라 목록 순서로 보낸다 — 서버가 상한에 닿았을 때 어디까지
    // 등록됐는지가 화면 순서와 어긋나지 않는다.
    const chosen = videos.filter((v) => selected.has(v.video_id));
    setIngesting(true);
    setBatchError(null);
    setSummary(null);
    try {
      const response = await apiFetch<{ results: IngestResult[] }>(
        `/workspaces/${workspaceId}/sources/youtube-videos`,
        {
          method: "POST",
          body: {
            channel_id: channel.channel_id,
            videos: chosen.map((v) => ({
              video_id: v.video_id,
              title: v.title,
            })),
          },
        },
      );
      const next: Record<string, IngestResult> = {};
      for (const result of response.results) next[result.video_id] = result;
      setResults((prev) => ({ ...prev, ...next }));
      setSummary(summarize(response.results));
      // 결과가 나온 영상은 선택에서 뺀다.
      setSelected(new Set());
      if (response.results.some((r) => r.reason === "budget_exceeded")) {
        setCreditLimitOpen(true);
      }
    } catch (caught) {
      // ⚠️ 요청 전체가 거부된 경우다(403 등). 영상별 결과와 섞지 않는다 — 섞으면
      //    "권한 없음"이 "일부 실패"로 보인다.
      setBatchError(
        caught instanceof ApiError && caught.status === 403
          ? BATCH_FORBIDDEN_MESSAGE
          : BATCH_GENERIC_MESSAGE,
      );
    } finally {
      setIngesting(false);
    }
  }

  return (
    <div className="flex flex-col gap-5">
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={onBack}
          className="inline-flex flex-none items-center gap-1.5 rounded-lg border border-[var(--border)] bg-[var(--surface)] px-3 py-1.5 text-xs font-semibold text-[var(--fg)]"
          data-testid="youtube-videos-back"
        >
          <ArrowLeft size={13} aria-hidden="true" />
          <span>채널 검색</span>
        </button>
        <p className="min-w-0 truncate text-sm font-bold text-[var(--fg)]">
          {channel.title}
        </p>
      </div>

      {error ? (
        <p
          role="alert"
          className="flex items-start gap-2 rounded-lg border border-[var(--warning)]/30 bg-[var(--warning)]/10 px-3 py-2.5 text-xs leading-relaxed text-[var(--fg)]"
          data-testid="youtube-videos-error"
        >
          <TriangleAlert
            size={14}
            className="mt-0.5 flex-none text-[var(--warning)]"
            aria-hidden="true"
          />
          <span>{error}</span>
        </p>
      ) : null}

      {batchError ? (
        <p
          role="alert"
          className="flex items-start gap-2 rounded-lg border border-[var(--warning)]/30 bg-[var(--warning)]/10 px-3 py-2.5 text-xs leading-relaxed text-[var(--fg)]"
          data-testid="youtube-batch-error"
        >
          <TriangleAlert
            size={14}
            className="mt-0.5 flex-none text-[var(--warning)]"
            aria-hidden="true"
          />
          <span>{batchError}</span>
        </p>
      ) : null}

      {loading ? (
        // 스피너 대신 실제 카드 모양의 스켈레톤을 깔아 로딩 → 목록 전환에서
        // 레이아웃이 튀지 않게 한다.
        <ul
          className="flex flex-col gap-2.5"
          aria-busy="true"
          aria-label="영상을 불러오는 중입니다"
          data-testid="youtube-videos-loading"
        >
          {[0, 1, 2].map((row) => (
            <li
              key={row}
              className="flex items-start gap-3 rounded-xl border border-[var(--border)] bg-[var(--bg)] p-3"
            >
              <span className="h-14 w-24 flex-none animate-pulse rounded-lg bg-[var(--surface)]" />
              <span className="flex min-w-0 flex-1 flex-col gap-2 pt-0.5">
                <span className="h-3.5 w-3/5 animate-pulse rounded bg-[var(--surface)]" />
                <span className="h-3 w-1/3 animate-pulse rounded bg-[var(--surface)]" />
              </span>
            </li>
          ))}
        </ul>
      ) : null}

      {videos.length > 0 ? (
        <>
          <div className="flex flex-wrap items-center justify-between gap-3">
            {/* ⚠️ "이 페이지 전체"가 아니라 "전체"다 — 이 목록은 페이지로 나뉘지 않고
                "더 보기"로 누적되므로, 여기서 선택되는 것은 **지금까지 불러온 전부**다.
                위키 문서 목록과 같은 pill + 카운트 배지 형태를 쓴다. */}
            <label
              className={`group inline-flex cursor-pointer items-center gap-2 rounded-full border px-3 py-1.5 transition-colors ${
                allSelected
                  ? "border-[var(--accent)]/40 bg-[var(--soft)] text-[var(--accent)]"
                  : selected.size > 0
                    ? "border-[var(--border-strong)] bg-[var(--surface)] text-[var(--fg)]"
                    : "border-[var(--border)] bg-[var(--surface)]/70 text-[var(--muted)] hover:border-[var(--border-strong)] hover:text-[var(--fg)]"
              } ${selectableIds.length === 0 ? "pointer-events-none opacity-50" : ""}`}
            >
              <input
                type="checkbox"
                checked={allSelected}
                onChange={toggleAll}
                disabled={selectableIds.length === 0}
                className="h-3.5 w-3.5 cursor-pointer accent-[var(--accent)]"
                data-testid="youtube-select-all"
              />
              <span className="text-[11.5px] font-semibold tracking-tight">
                {selected.size > 0 ? `${selected.size}편 선택됨` : "전체 선택"}
              </span>
              <span
                className={`rounded-full px-1.5 py-0.5 font-mono text-[10px] font-bold transition-colors ${
                  allSelected
                    ? "bg-[var(--accent)] text-white"
                    : "border border-[var(--border)] bg-[var(--bg)] text-[var(--muted)] group-hover:text-[var(--fg)]"
                }`}
              >
                {selectableIds.length}
              </span>
            </label>
            <button
              type="button"
              onClick={handleIngestSelected}
              disabled={selected.size === 0 || ingesting}
              className="inline-flex items-center gap-1.5 rounded-lg bg-[var(--accent)] px-4 py-2 text-sm font-semibold text-white transition-all active:translate-y-px disabled:pointer-events-none disabled:opacity-50"
              data-testid="youtube-ingest-selected"
            >
              {ingesting ? (
                <Loader2
                  size={14}
                  className="animate-spin"
                  aria-hidden="true"
                />
              ) : null}
              <span>
                {selected.size > 0
                  ? `${selected.size}편 수집`
                  : "수집할 영상 선택"}
              </span>
            </button>
          </div>

          {summary ? (
            <p
              role="status"
              className="rounded-lg border border-[var(--border)] bg-[var(--surface)] px-3 py-2 text-xs font-semibold text-[var(--fg)]"
              data-testid="youtube-batch-summary"
            >
              {summary}
            </p>
          ) : null}

          <ul className="flex flex-col gap-2.5">
            {videos.map((video) => {
              const result = results[video.video_id];
              const isSelected = selected.has(video.video_id);
              return (
                <li key={video.video_id}>
                  {/* ⚠️ `<label>`로 감싸 카드 전체가 선택 영역이 된다. onClick 핸들러를
                      두는 대신 네이티브 라벨-입력 연결을 쓰는 이유: 키보드 포커스·
                      스페이스바 토글·스크린리더 안내가 전부 공짜로 따라오고,
                      카드 안에 다른 상호작용 요소가 없어 충돌할 것도 없다.
                      체크박스는 `sr-only`로 남겨 접근성과 테스트 훅을 유지한다. */}
                  <label
                    className={`flex items-start gap-3 rounded-xl border p-3 transition-all ${
                      result
                        ? "cursor-default border-[var(--border)] bg-[var(--surface)]/40"
                        : isSelected
                          ? "cursor-pointer border-[var(--accent)] bg-[var(--soft)]/40 ring-1 ring-[var(--accent)]/40 active:translate-y-px"
                          : "cursor-pointer border-[var(--border)] bg-[var(--bg)] hover:border-[var(--border-strong)] hover:bg-[var(--surface)] active:translate-y-px"
                    } ${result ? "" : "select-none"}`}
                    data-testid={`youtube-video-${video.video_id}`}
                  >
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => toggle(video.video_id)}
                      disabled={Boolean(result)}
                      aria-label={`${video.title} 선택`}
                      className="sr-only"
                      data-testid={`youtube-video-select-${video.video_id}`}
                    />
                    {video.thumbnail_url ? (
                      // eslint-disable-next-line @next/next/no-img-element -- 외부 CDN 썸네일이라 next/image 도메인 설정 대상이 아니다
                      <img
                        src={video.thumbnail_url}
                        alt=""
                        className="h-14 w-24 flex-none rounded-lg object-cover"
                      />
                    ) : (
                      <span
                        className="flex h-14 w-24 flex-none items-center justify-center rounded-lg bg-[var(--surface)]"
                        aria-hidden="true"
                      >
                        <MonitorPlay
                          size={16}
                          className="text-[var(--muted)]"
                        />
                      </span>
                    )}
                    <div className="min-w-0 flex-1">
                      <p className="line-clamp-2 text-sm font-semibold text-[var(--fg)]">
                        {video.title}
                      </p>
                      <p className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-xs text-[var(--muted)]">
                        <span>{formatDuration(video.duration_seconds)}</span>
                        {formatPublishedAt(video.published_at) ? (
                          <>
                            <span aria-hidden="true">·</span>
                            <span>{formatPublishedAt(video.published_at)}</span>
                          </>
                        ) : null}
                        {formatCount(video.view_count) ? (
                          <>
                            <span aria-hidden="true">·</span>
                            <span>
                              조회수 {formatCount(video.view_count)}회
                            </span>
                          </>
                        ) : null}
                        {formatCount(video.like_count) ? (
                          <>
                            <span aria-hidden="true">·</span>
                            <span>
                              좋아요 {formatCount(video.like_count)}개
                            </span>
                          </>
                        ) : null}
                      </p>
                      {/* ⚠️ has_captions는 확정 판정이 아니라 힌트다 — 배지가 없어도
                          선택은 계속 가능하다(design.md Non-Goals). */}
                      {video.has_captions === false ? (
                        <span
                          className="mt-1 inline-flex items-center gap-1 rounded-full bg-[var(--warning)]/10 px-2 py-0.5 text-[10.5px] font-semibold text-[var(--warning)]"
                          data-testid={`youtube-video-no-captions-${video.video_id}`}
                        >
                          자막 없을 수 있음
                        </span>
                      ) : null}
                    </div>
                    {result ? (
                      <span
                        className={`inline-flex flex-none items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold ${
                          result.status === "failed"
                            ? "text-[var(--warning)]"
                            : "bg-[var(--surface)] text-[var(--muted)]"
                        }`}
                        data-testid={`youtube-video-status-${video.video_id}`}
                      >
                        {result.status === "failed" ? (
                          <TriangleAlert size={13} aria-hidden="true" />
                        ) : (
                          <Check size={13} aria-hidden="true" />
                        )}
                        <span>{resultLabel(result)}</span>
                      </span>
                    ) : (
                      // 선택 여부를 카드 오른쪽에서도 읽을 수 있게 한다 — 테두리 색만으로는
                      // 목록이 길어질 때 훑어보기 어렵다.
                      <span
                        aria-hidden="true"
                        className={`mt-0.5 flex h-4 w-4 flex-none items-center justify-center rounded border transition-colors ${
                          isSelected
                            ? "border-[var(--accent)] bg-[var(--accent)] text-white"
                            : "border-[var(--border-strong)] bg-[var(--bg)]"
                        }`}
                      >
                        {isSelected ? (
                          <Check size={11} strokeWidth={3} />
                        ) : null}
                      </span>
                    )}
                  </label>
                </li>
              );
            })}
          </ul>
        </>
      ) : null}

      {nextPageToken ? (
        <button
          type="button"
          onClick={handleLoadMore}
          disabled={loadingMore}
          className="mx-auto inline-flex items-center gap-1.5 rounded-lg border border-[var(--border)] bg-[var(--surface)] px-4 py-2 text-xs font-semibold text-[var(--fg)] disabled:opacity-50"
          data-testid="youtube-videos-more"
        >
          {loadingMore ? (
            <Loader2 size={13} className="animate-spin" aria-hidden="true" />
          ) : null}
          <span>영상 더 보기</span>
        </button>
      ) : null}

      {!loading && !error && videos.length === 0 ? (
        <div className="flex flex-col items-center gap-2 rounded-xl border border-dashed border-[var(--border)] px-4 py-10 text-center">
          <MonitorPlay
            size={20}
            className="text-[var(--muted)]"
            aria-hidden="true"
          />
          <p className="text-sm font-semibold text-[var(--fg)]">
            수집할 수 있는 영상이 없습니다
          </p>
          <p className="text-xs leading-relaxed text-[var(--muted)]">
            이 채널은 공개된 영상을 올리지 않았습니다. 검색으로 돌아가 다른
            채널을 골라 주세요.
          </p>
          <button
            type="button"
            onClick={onBack}
            className="mt-1 inline-flex items-center gap-1.5 rounded-lg border border-[var(--border)] bg-[var(--surface)] px-3 py-1.5 text-xs font-semibold text-[var(--fg)] transition-all active:translate-y-px"
          >
            <ArrowLeft size={13} aria-hidden="true" />
            <span>채널 검색</span>
          </button>
        </div>
      ) : null}

      <CreditLimitModal
        open={creditLimitOpen}
        onOpenChange={setCreditLimitOpen}
        workspaceId={workspaceId}
      />
    </div>
  );
}

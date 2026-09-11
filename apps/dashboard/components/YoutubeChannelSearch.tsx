"use client";

import {
  ChevronRight,
  Loader2,
  MonitorPlay,
  Search,
  TriangleAlert,
} from "lucide-react";
import { useState } from "react";

import { YoutubeVideoList } from "@/components/YoutubeVideoList";
import { ApiError, apiFetch } from "@/lib/api-client";

export type YoutubeChannel = {
  channel_id: string;
  title: string;
  description: string;
  thumbnail_url: string | null;
};

type ChannelSearchResponse = {
  channels: YoutubeChannel[];
  next_page_token: string | null;
};

export type YoutubeChannelSearchProps = {
  workspaceId: string;
};

// ⚠️ 문구를 detail 토큰별로 고른다. 서버는 짧은 기계 판독 토큰만 내려주고
//    (`api/errors.py`의 InvalidSourceInput 주석과 같은 규약) 문장은 여기 산다 —
//    반대로 하면 UI 문구를 바꾸는 데 API 배포가 필요해진다.
const QUOTA_MESSAGE =
  "오늘 사용할 수 있는 YouTube 검색 횟수를 모두 썼습니다. 내일 다시 시도하거나, 이미 검색해 둔 채널로 진행해 주세요.";
const UNAVAILABLE_MESSAGE =
  "YouTube 검색에 연결하지 못했습니다. 잠시 후 다시 시도해 주세요.";
const FORBIDDEN_MESSAGE = "이 워크스페이스에서 검색할 권한이 없습니다.";
const GENERIC_MESSAGE = "검색에 실패했습니다. 잠시 후 다시 시도해 주세요.";

function messageFor(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.detail === "youtube_quota_exceeded") return QUOTA_MESSAGE;
    if (error.detail === "youtube_unavailable") return UNAVAILABLE_MESSAGE;
    if (error.status === 403) return FORBIDDEN_MESSAGE;
  }
  return GENERIC_MESSAGE;
}

export function YoutubeChannelSearch({
  workspaceId,
}: YoutubeChannelSearchProps) {
  const [query, setQuery] = useState("");
  const [channels, setChannels] = useState<YoutubeChannel[]>([]);
  const [nextPageToken, setNextPageToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searched, setSearched] = useState(false);
  const [selected, setSelected] = useState<YoutubeChannel | null>(null);

  async function fetchPage(pageToken: string | null) {
    const params = new URLSearchParams({ q: query.trim() });
    if (pageToken) params.set("page_token", pageToken);
    return apiFetch<ChannelSearchResponse>(
      `/workspaces/${workspaceId}/youtube/channels?${params.toString()}`,
    );
  }

  async function handleSearch(event: React.FormEvent) {
    event.preventDefault();
    if (!query.trim() || loading) return;
    setLoading(true);
    setError(null);
    try {
      const result = await fetchPage(null);
      setChannels(result.channels);
      setNextPageToken(result.next_page_token);
    } catch (caught) {
      // ⚠️ 실패했을 때 이전 결과를 그대로 두면 사용자는 새 검색이 성공했다고 믿는다.
      setChannels([]);
      setNextPageToken(null);
      setError(messageFor(caught));
    } finally {
      setSearched(true);
      setLoading(false);
    }
  }

  async function handleLoadMore() {
    if (!nextPageToken || loadingMore) return;
    setLoadingMore(true);
    setError(null);
    try {
      const result = await fetchPage(nextPageToken);
      setChannels((prev) => [...prev, ...result.channels]);
      setNextPageToken(result.next_page_token);
    } catch (caught) {
      // 더 보기 실패는 이미 받은 목록을 지우지 않는다 — 지울 이유가 없다.
      setError(messageFor(caught));
    } finally {
      setLoadingMore(false);
    }
  }

  // ⚠️ 채널을 고르면 검색 UI를 **대체한다.** 두 목록을 같은 화면에 두면 "영상 더 보기"와
  //    "채널 더 보기"가 나란히 놓여 어느 목록이 늘어나는지가 사라진다. 검색 상태는
  //    언마운트되지 않으므로 뒤로 가면 방금 검색한 결과가 그대로 남는다.
  if (selected) {
    return (
      <YoutubeVideoList
        workspaceId={workspaceId}
        channel={selected}
        onBack={() => setSelected(null)}
      />
    );
  }

  return (
    <div className="mt-8 flex flex-col gap-6">
      <form onSubmit={handleSearch} className="flex items-center gap-2">
        <div className="relative flex-1">
          <Search
            size={15}
            className="pointer-events-none absolute top-1/2 left-3 -translate-y-1/2 text-[var(--muted)]"
            aria-hidden="true"
          />
          <input
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="채널을 검색할 키워드 (예: 요리, 스타트업)"
            aria-label="채널 검색 키워드"
            maxLength={100}
            className="w-full rounded-lg border border-[var(--border)] bg-[var(--surface)] py-2 pr-3 pl-9 text-sm text-[var(--fg)] placeholder:text-[var(--muted)] focus:border-[var(--accent)] focus:outline-none"
            data-testid="youtube-search-input"
          />
        </div>
        <button
          type="submit"
          disabled={!query.trim() || loading}
          className="inline-flex flex-none items-center gap-1.5 rounded-lg bg-[var(--accent)] px-4 py-2 text-sm font-semibold text-white transition-opacity disabled:opacity-50"
          data-testid="youtube-search-submit"
        >
          {loading ? (
            <Loader2 size={14} className="animate-spin" aria-hidden="true" />
          ) : null}
          <span>검색</span>
        </button>
      </form>

      {error ? (
        <p
          role="alert"
          className="flex items-start gap-2 rounded-lg border border-[var(--warning)]/30 bg-[var(--warning)]/10 px-3 py-2.5 text-xs leading-relaxed text-[var(--fg)]"
          data-testid="youtube-search-error"
        >
          <TriangleAlert
            size={14}
            className="mt-0.5 flex-none text-[var(--warning)]"
            aria-hidden="true"
          />
          <span>{error}</span>
        </p>
      ) : null}

      {channels.length > 0 ? (
        <ul className="grid grid-cols-1 gap-3 md:grid-cols-2">
          {channels.map((channel) => (
            <li key={channel.channel_id}>
              <button
                type="button"
                onClick={() => setSelected(channel)}
                className="group flex w-full items-start gap-3 rounded-xl border border-[var(--border)] bg-[var(--bg)] p-3.5 text-left transition-all hover:border-[var(--border-strong)] hover:bg-[var(--surface)] active:translate-y-px"
                data-testid={`youtube-channel-${channel.channel_id}`}
              >
                {channel.thumbnail_url ? (
                  // eslint-disable-next-line @next/next/no-img-element -- 외부 CDN 썸네일이라 next/image 도메인 설정 대상이 아니다
                  <img
                    src={channel.thumbnail_url}
                    alt=""
                    className="h-11 w-11 flex-none rounded-full object-cover"
                  />
                ) : (
                  <span
                    className="flex h-11 w-11 flex-none items-center justify-center rounded-full bg-[var(--surface)]"
                    aria-hidden="true"
                  >
                    <MonitorPlay size={16} className="text-[var(--muted)]" />
                  </span>
                )}
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-bold text-[var(--fg)]">
                    {channel.title}
                  </p>
                  <p className="mt-0.5 line-clamp-2 text-xs leading-relaxed text-[var(--muted)]">
                    {channel.description || "설명이 없는 채널입니다."}
                  </p>
                </div>
                {/* 이 카드가 "선택"이 아니라 "영상 목록으로 이동"이라는 것을 알린다 —
                    영상 카드의 체크 표시와 형태를 다르게 둬 두 상호작용을 구분한다. */}
                <ChevronRight
                  size={15}
                  aria-hidden="true"
                  className="mt-0.5 flex-none text-[var(--muted)] transition-transform group-hover:translate-x-0.5 group-hover:text-[var(--fg)]"
                />
              </button>
            </li>
          ))}
        </ul>
      ) : null}

      {nextPageToken ? (
        <button
          type="button"
          onClick={handleLoadMore}
          disabled={loadingMore}
          className="mx-auto inline-flex items-center gap-1.5 rounded-lg border border-[var(--border)] bg-[var(--surface)] px-4 py-2 text-xs font-semibold text-[var(--fg)] disabled:opacity-50"
          data-testid="youtube-search-more"
        >
          {loadingMore ? (
            <Loader2 size={13} className="animate-spin" aria-hidden="true" />
          ) : null}
          <span>채널 더 보기</span>
        </button>
      ) : null}

      {searched && !loading && !error && channels.length === 0 ? (
        <div className="flex flex-col items-center gap-2 rounded-xl border border-dashed border-[var(--border)] px-4 py-10 text-center">
          <Search
            size={20}
            className="text-[var(--muted)]"
            aria-hidden="true"
          />
          <p className="text-sm font-semibold text-[var(--fg)]">
            검색 결과가 없습니다
          </p>
          <p className="text-xs leading-relaxed text-[var(--muted)]">
            채널명의 일부만 넣거나 더 일반적인 키워드로 다시 시도해 보세요.
          </p>
        </div>
      ) : null}

      {/* 아직 검색하지 않은 상태. 빈 화면을 그대로 두면 이 페이지가 무엇을 하는
          곳인지 입력창 하나로만 설명하게 된다. */}
      {!searched && !loading && !error ? (
        <div className="flex flex-col items-center gap-2 rounded-xl border border-dashed border-[var(--border)] px-4 py-12 text-center">
          <MonitorPlay
            size={20}
            className="text-[var(--muted)]"
            aria-hidden="true"
          />
          <p className="text-sm font-semibold text-[var(--fg)]">
            채널을 검색해 시작하세요
          </p>
          <p className="max-w-sm text-xs leading-relaxed text-[var(--muted)]">
            채널을 고르면 영상 목록이 열립니다. 거기서 원하는 영상만 선택하면
            자막이 원문 소스로 수집됩니다.
          </p>
        </div>
      ) : null}
    </div>
  );
}

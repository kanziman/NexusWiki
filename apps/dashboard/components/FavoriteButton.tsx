"use client";

import { Star } from "lucide-react";
import { useState } from "react";

import { setWikiBookmark } from "@/app/bookmark-actions";

export type FavoriteButtonProps = {
  wikiId: string;
  workspaceId: string;
  initialBookmarked: boolean;
};

// 낙관적으로 상태를 먼저 바꾸고 실패하면 되돌린다 — 별표 하나 토글에
// 서버 왕복을 기다리게 하지 않는다. LNB "즐겨찾기"는 별도 페이지
// (wiki?bookmarked=true)로의 정적 링크일 뿐 이 버튼이 그릴 실시간 목록이
// 없어 router.refresh()로 갱신할 대상이 없다.
export function FavoriteButton({
  wikiId,
  workspaceId,
  initialBookmarked,
}: FavoriteButtonProps) {
  const [bookmarked, setBookmarked] = useState(initialBookmarked);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleClick() {
    if (pending) return;
    const next = !bookmarked;
    setPending(true);
    setError(null);
    setBookmarked(next);

    const result = await setWikiBookmark(wikiId, workspaceId, next);
    if ("error" in result) {
      setBookmarked(!next);
      setError(result.error);
    }
    setPending(false);
  }

  return (
    <span className="relative inline-flex">
      <button
        type="button"
        onClick={handleClick}
        disabled={pending}
        className={`star${bookmarked ? " is-on" : ""}`}
        data-od-id="favorite-control"
        aria-pressed={bookmarked}
        aria-label={bookmarked ? "즐겨찾기 해제" : "즐겨찾기에 추가"}
      >
        <Star size={18} aria-hidden="true" />
      </button>
      {/* title-row(display:flex)의 직접 자식이 되지 않도록 이 span 안에서만
          절대 위치시킨다 — 그냥 형제로 두면 h1·별표 옆에 나란히 끼어든다. */}
      {error !== null ? (
        <p
          role="alert"
          className="invite-feedback error show absolute top-full left-0 z-10 mt-1 whitespace-nowrap"
        >
          {error}
        </p>
      ) : null}
    </span>
  );
}

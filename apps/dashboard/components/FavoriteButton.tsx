"use client";

import { Star } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { toggleWikiBookmark } from "@/app/bookmark-actions";

export type FavoriteButtonProps = {
  wikiId: string;
  workspaceId: string;
  initialBookmarked: boolean;
};

// LNB의 즐겨찾기 목록은 서버 컴포넌트(WorkspaceSidebar 상위)가 그린다 —
// 토글 성공 후 router.refresh()로 그 목록을 함께 최신화한다.
export function FavoriteButton({
  wikiId,
  workspaceId,
  initialBookmarked,
}: FavoriteButtonProps) {
  const router = useRouter();
  const [bookmarked, setBookmarked] = useState(initialBookmarked);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleClick() {
    if (pending) return;
    setPending(true);
    setError(null);

    const result = await toggleWikiBookmark(wikiId, workspaceId);
    if ("error" in result) {
      setError(result.error);
    } else {
      setBookmarked(result.bookmarked);
      router.refresh();
    }
    setPending(false);
  }

  return (
    <>
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
      {error !== null ? (
        <p role="alert" className="invite-feedback error show">
          {error}
        </p>
      ) : null}
    </>
  );
}

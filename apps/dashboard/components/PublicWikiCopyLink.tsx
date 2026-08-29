"use client";

import { useState } from "react";
import { Link2 } from "lucide-react";

const COPY_SUCCESS = "링크를 복사했습니다.";
const COPY_FAILURE = "링크를 복사하지 못했습니다. 다시 시도해주세요.";

export function PublicWikiCopyLink() {
  const [status, setStatus] = useState<string | null>(null);

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(window.location.href);
      setStatus(COPY_SUCCESS);
    } catch {
      setStatus(COPY_FAILURE);
    }
  }

  return (
    <>
      <button
        type="button"
        className="public-btn-secondary"
        onClick={() => {
          void handleCopy();
        }}
      >
        <Link2 size={12} strokeWidth={2} aria-hidden="true" />
        링크 복사
      </button>
      <span className="sr-only" aria-live="polite">
        {status ?? ""}
      </span>
    </>
  );
}

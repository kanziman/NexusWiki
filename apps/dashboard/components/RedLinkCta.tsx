"use client";

import { Plus } from "lucide-react";
import { useRouter } from "next/navigation";

import { workspacePath } from "@/lib/workspace-path";

export type RedLinkCtaProps = {
  title: string;
  slug: string;
  workspaceId: string;
};

// UI-SPEC Copywriting Contract "Red-link CTA (verbatim)" — 문구를 한 글자도
// 바꾸지 않는다.
const RED_LINK_LABEL = "아직 작성되지 않음 · 지금 생성";
// UI-SPEC Spacing Scale "Icon-only touch targets" 3종 중 하나 — 문구도 고정.
const CREATE_ICON_LABEL = "지금 생성";

/**
 * 미해결(red) WikiLink의 미니멀 인라인 CTA — `wiki_pages`에 없는 대상을 가리키는
 * `[[제목]]`이 본문 흐름을 깨뜨리지 않고 자연스럽게 렌더링된다.
 */
export function RedLinkCta({ title, slug, workspaceId }: RedLinkCtaProps) {
  const router = useRouter();

  function handleCreate(e?: React.MouseEvent) {
    e?.stopPropagation();
    router.push(
      `${workspacePath(workspaceId)}/sources?prefillTitle=${encodeURIComponent(title)}&tab=text`,
    );
  }

  return (
    <span
      data-testid="red-link-cta"
      data-slug={slug}
      className="group inline-flex items-center gap-1.5 align-baseline text-[13px] text-[var(--danger)]/90 hover:text-[var(--danger)] transition-colors"
    >
      {/* 제목 텍스트 — 미작성임을 나타내는 점선 밑줄 */}
      <span
        className="font-medium text-[var(--danger)] underline decoration-dashed decoration-[var(--danger)]/40 underline-offset-4 group-hover:decoration-[var(--danger)] transition-all max-w-[240px] truncate align-baseline"
        style={{
          display: "-webkit-box",
          WebkitLineClamp: 2,
          WebkitBoxOrient: "vertical",
          overflow: "hidden",
        }}
      >
        {title}
      </span>

      {/* 심플한 플러스 아이콘 버튼 */}
      <button
        type="button"
        onClick={handleCreate}
        aria-label={CREATE_ICON_LABEL}
        className="inline-flex h-4 w-4 items-center justify-center rounded text-[var(--danger)]/80 group-hover:text-[var(--danger)] group-hover:bg-[var(--danger)]/10 transition-colors flex-none"
      >
        <Plus size={12} strokeWidth={2.2} aria-hidden="true" />
      </button>

      {/* 미니멀 상태 라벨 */}
      <span className="text-[11px] font-normal text-[var(--muted)] group-hover:text-[var(--danger)]/80 transition-colors whitespace-nowrap">
        {RED_LINK_LABEL}
      </span>
    </span>
  );
}

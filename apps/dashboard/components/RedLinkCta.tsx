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
 * 미해결(red) WikiLink의 인라인 CTA — `wiki_pages`에 없는 대상을 가리키는
 * `[[제목]]`이 렌더링된다.
 *
 * 관련 태스크: 06-07-PLAN.md Task 3
 * 설계 근거: 06-UI-SPEC.md "UI Considerations" long-text/red-link-cta 행(2줄
 *            clamp backstop), Spacing Scale Exceptions(44×44px 아이콘 히트
 *            영역 + aria-label)
 *
 * ⚠️ 클릭은 새 소스를 만드는 화면으로 이동할 뿐이다 — `wiki_pages` 행을 직접
 * 만들거나 고치는 경로는 v1에 없다(자유 편집 없음, PROJECT.md Key Decisions).
 * 실제 위키 페이지는 컴파일러가 이후 잡 체인에서 만든다.
 */
export function RedLinkCta({ title, slug, workspaceId }: RedLinkCtaProps) {
  const router = useRouter();

  function handleCreate() {
    // 06-07-PLAN.md Task 3 <action>이 명시한 그대로 — URLSearchParams가 아니라
    // encodeURIComponent로 직접 조립한다(URLSearchParams는 공백을 `+`로
    // 인코딩해 이 경로의 기대 형태와 어긋난다).
    router.push(
      `${workspacePath(workspaceId)}/sources?prefillTitle=${encodeURIComponent(title)}&tab=text`,
    );
  }

  return (
    <span
      data-testid="red-link-cta"
      data-slug={slug}
      className="inline-flex items-center gap-xs align-middle"
    >
      <span
        className="inline-block max-w-[240px] align-middle"
        style={{
          font: "var(--font-body-md)",
          display: "-webkit-box",
          WebkitLineClamp: 2,
          WebkitBoxOrient: "vertical",
          overflow: "hidden",
        }}
      >
        {title}
      </span>
      <button
        type="button"
        onClick={handleCreate}
        aria-label={CREATE_ICON_LABEL}
        className="inline-flex h-11 w-11 items-center justify-center rounded-full text-primary"
      >
        <Plus size={20} aria-hidden="true" />
      </button>
      <span className="text-primary" style={{ font: "var(--font-caption)" }}>
        {RED_LINK_LABEL}
      </span>
    </span>
  );
}

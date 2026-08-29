export type WikiHeading = {
  id: string;
  level: number;
  title: string;
};

const RELATED_DOCS_TAIL =
  /(?:\r?\n)+(?:#{1,4}[ \t]*)?(?:\*\*)?(?:관련\s*문서|관련문서|Related\s*Documents?)(?:\*\*)?(?:[ \t]*[:：][ \t]*|[ \t]*(?:\r?\n|$))[\s\S]*$/i;

/**
 * 마크다운 본문 끝의 중복 "관련 문서" 섹션을 제거한다. 내부 리더는 카드 UI로
 * 바꾸고, 공개 리더는 내부 라우트를 만들지 않으려고 같은 구간을 버린다.
 */
export function cleanWikiContent(content: string): string {
  if (!content) return "";
  return content.replace(RELATED_DOCS_TAIL, "").trimEnd();
}

export function extractHeadings(content: string): WikiHeading[] {
  if (!content) return [];
  const lines = content.split("\n");
  const result: WikiHeading[] = [];

  for (let index = 0; index < lines.length; index++) {
    const match = /^(#{1,4})\s+(.+?)\s*$/.exec(lines[index]);
    if (!match) continue;
    const rawTitle = match[2]
      .replace(/\[\[(?:[^\]|]+\|)?([^\]]+)\]\]/g, "$1")
      .replace(/[*_`~]/g, "")
      .trim();
    result.push({
      id: `section-${index}`,
      level: match[1].length,
      title: rawTitle,
    });
  }

  return result;
}

/** 공개 URL. 세그먼트를 인코딩해 슬러그의 한글·공백이 경로를 쪼개지 않게 한다. */
export function publicWikiPath(
  workspaceSlug: string,
  pageSlug: string,
): string {
  return `/p/${encodeURIComponent(workspaceSlug)}/${encodeURIComponent(pageSlug)}`;
}

/** 한글 본문 기준 대략 분당 400자. 빈 문서는 1분으로 올린다. */
export function estimateReadMinutes(content: string): number {
  const chars = content.replace(/\s+/g, "").length;
  return Math.max(1, Math.round(chars / 400) || 1);
}

export function workspaceInitials(name: string): string {
  const compact = name.replace(/\s+/g, "");
  return compact.slice(0, 2) || "NW";
}

/** 공개 인용 카드에 원문 마크다운 문법이 그대로 보이지 않게 평문으로 접는다. */
export function plainCitationSnippet(text: string, maxChars = 240): string {
  if (!text) return "";
  const stripped = text
    .replace(/```[\s\S]*?```/g, " ")
    .replace(/`([^`]+)`/g, "$1")
    .replace(/#{1,6}\s+/g, "")
    .replace(/\*\*([^*]+)\*\*/g, "$1")
    .replace(/__([^_]+)__/g, "$1")
    .replace(/\*([^*]+)\*/g, "$1")
    .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1")
    .replace(/\[\[(?:[^\]|]+\|)?([^\]]+)\]\]/g, "$1")
    .replace(/[ \t]+/g, " ")
    .replace(/\n{2,}/g, "\n")
    .trim();
  if (stripped.length <= maxChars) return stripped;
  return `${stripped.slice(0, maxChars)}…`;
}

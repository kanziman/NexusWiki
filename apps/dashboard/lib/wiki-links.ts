/**
 * `wiki_pages.content`에 박힌 `[[제목]]` WikiLink 문법을 파싱하고 해소하는 순수 함수.
 *
 * 관련 태스크: 06-07-PLAN.md Task 1
 * 설계 근거: packages/core/src/nexuswiki_core/slug.py (`_base_slug` — 이 파일의
 *            `baseSlug`가 포팅하는 원본), packages/core/src/nexuswiki_core/tokenizer.py
 *            (`normalize` — NFKC -> casefold -> NFKC -> 공백 정규화 순서 계약),
 *            apps/worker/src/worker/handlers/link_sync.py (`\[\[([^\]]+)\]\]` — 이
 *            모듈이 스캔하는 것과 동일한 WikiLink 정규식)
 *
 * ⚠️ 이 정규식은 06-06-PLAN.md `lib/citation-anchors.ts`의
 * `ISSUED_ANCHOR_PATTERN`(`[[wiki:w1]]`/`[[src:s1]]`)과 문법이 전혀 다르다. 전자는
 * Ask 스트리밍 응답에만 나타나는 서버 발급 인용 앵커이고, 이 모듈이 다루는 것은
 * 컴파일된 `wiki_pages.content`에 LLM이 남기는 `[[페이지 제목]]` 상호 링크다. 두
 * `[[...]]` 문법을 하나로 합치면 안 된다(설계 근거 참조).
 *
 * ⚠️ 알려진 한계 (안전한 실패 — 06-07-PLAN.md assumptions):
 * 1. `taken` 충돌 접미(`-2`, `-3`, ...) 해소는 포팅하지 않는다 — 서버 측
 *    `slugify()`가 드물게 충돌을 `-2` 접미로 해소한 경우, 클라이언트가 재계산한
 *    `baseSlug()`는 그 접미 없는 값을 내어 실제로는 존재하는 페이지도 레드
 *    링크(미해결)로 보인다. 최악의 경우가 "동작하는 링크에 불필요한 생성 CTA가
 *    뜨는 것"뿐이라 데이터 손실 없는 안전한 실패다.
 * 2. `normalize()`는 Python `str.casefold()`를 `String.prototype.toLowerCase()`로
 *    근사한다 — 두 함수는 일부 유니코드 대소문자 폴딩 규칙(예: 독일어 에스체트,
 *    터키어 점 없는 i)에서 바이트 단위로 다르다. 이 모듈은 표시 전용이라 근사를
 *    허용한다.
 * 3. `baseSlug("")`(또는 전부 비허용 문자)의 폴백은 Python의 SHA-256 폴백을
 *    문자 단위로 재현하지 않는다 — 결정적이기만 하면 되는 표시 전용 경로이고,
 *    실전 컴파일 콘텐츠에서 거의 도달하지 않는 경로다.
 */

const DISALLOWED = /[^0-9a-z가-힣-]/gu;
const HYPHEN_RUN = /-{2,}/g;
const SLUG_MAX_LENGTH = 80;
const FALLBACK_PREFIX = "page-";

const WIKI_LINK_PATTERN = /\[\[([^\]]+)\]\]/g;

export type WikiLinkPart =
  | { type: "text"; value: string }
  | { type: "link"; title: string; resolved: boolean; slug: string };

/**
 * `nexuswiki_core.tokenizer.normalize`의 JS 근사판.
 *
 * NFKC -> toLowerCase (casefold 근사, 위 한계 #2 참조) -> NFKC 재적용
 * (toLowerCase가 호환 문자를 되살릴 수 있어 멱등성을 위해 필요) -> 공백 정규화.
 */
function normalize(text: string): string {
  const composed = text.normalize("NFKC");
  const folded = composed.toLowerCase().normalize("NFKC");
  return folded.replace(/\s+/g, " ").trim();
}

function truncate(slug: string, limit: number): string {
  return slug.slice(0, limit).replace(/^-+|-+$/g, "");
}

/**
 * 허용 문자가 하나도 남지 않았을 때의 폴백. Python의 SHA-256 폴백을 문자 단위로
 * 재현하지 않는다 — 위 한계 #3 참조. `slug` NOT NULL/비어있지 않음 계약만 지킨다.
 */
function fallbackSlug(normalized: string): string {
  let hash = 0;
  for (let index = 0; index < normalized.length; index += 1) {
    hash = (hash * 31 + normalized.charCodeAt(index)) | 0;
  }
  const hex = (hash >>> 0).toString(16).padStart(8, "0");
  return `${FALLBACK_PREFIX}${hex}`;
}

/**
 * `nexuswiki_core.slug._base_slug`를 포팅한다: NFKC 정규화 -> 공백을 하이픈으로
 * 치환 -> `[0-9a-z가-힣-]` 밖 문자 제거 -> 연속 하이픈 축약 -> 앞뒤 하이픈 제거 ->
 * 80자 절단. 충돌 접미(`-2`) 해소는 서버 전용이라 포팅하지 않는다(위 한계 #1).
 */
export function baseSlug(title: string): string {
  const normalized = normalize(title);
  const hyphenated = normalized.replace(/ /g, "-");
  const filtered = hyphenated.replace(DISALLOWED, "");
  const collapsed = filtered.replace(HYPHEN_RUN, "-").replace(/^-+|-+$/g, "");

  const truncated = truncate(collapsed, SLUG_MAX_LENGTH);
  return truncated.length > 0 ? truncated : fallbackSlug(normalized);
}

/**
 * `content` 안의 `[[제목]]` WikiLink를 `links`(해당 페이지의 `wiki_links` 행)와
 * 대조해 text/link part의 순서 있는 배열로 분리한다.
 *
 * 매치된 제목은 `link_sync.py`의 `x.strip()`과 같은 방식으로 트림한 뒤
 * `baseSlug()`를 적용해 `target_slug`와 대조한다. 대조되는 행이 없으면(아직
 * `link_sync` 잡이 돌지 않았거나, 정말 없는 대상) `resolved: false`이고
 * `slug`에는 계산된 `baseSlug` 값을 그대로 실어 red-link CTA의 소스-생성 prefill이
 * 쓸 슬러그 모양 식별자를 보장한다.
 */
export function resolveWikiLinks(
  content: string,
  links: { target_slug: string; resolved: boolean }[],
): WikiLinkPart[] {
  const linksBySlug = new Map(links.map((link) => [link.target_slug, link]));
  const parts: WikiLinkPart[] = [];
  let lastIndex = 0;

  for (const match of content.matchAll(WIKI_LINK_PATTERN)) {
    const matchIndex = match.index ?? 0;
    if (matchIndex > lastIndex) {
      parts.push({ type: "text", value: content.slice(lastIndex, matchIndex) });
    }

    const title = match[1].trim();
    const slug = baseSlug(title);
    const found = linksBySlug.get(slug);

    parts.push({
      type: "link",
      title,
      resolved: found?.resolved ?? false,
      slug: found?.target_slug ?? slug,
    });

    lastIndex = matchIndex + match[0].length;
  }

  if (lastIndex < content.length) {
    parts.push({ type: "text", value: content.slice(lastIndex) });
  }

  if (parts.length === 0) {
    parts.push({ type: "text", value: content });
  }

  return parts;
}

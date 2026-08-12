/**
 * 서버 발급 인용 앵커(`[[wiki:w1]]`/`[[src:s1]]`)를 text/anchor part로 분리하는
 * 순수 함수 — `nexuswiki_core/citations.py`의 `ISSUED_ANCHOR_PATTERN`과
 * `apps/api/src/api/services/ask.py`의 `resolve_citations()`를 클라이언트에서
 * 그대로 미러링한다.
 *
 * 관련 태스크: 06-06-PLAN.md Task 1
 * 설계 근거: packages/core/src/nexuswiki_core/citations.py (정규식 문법의 단일
 *            출처), apps/api/src/api/services/ask.py:147-192 (resolve_citations —
 *            "파싱된 앵커 ∩ 발급된 앵커"만 남기고 나머지는 조용히 지운다)
 *
 * ⚠️ `BROAD_ANCHOR_PATTERN`은 여기서 포팅하지 않는다 — 위조 앵커 제거(CITE-06)는
 * 이미 수집 시점에 서버에서 끝났다(strip_forged_anchors, chunk_text() 이전 1회).
 * 이 요청이 실제로 발급한 좁은 `ISSUED_ANCHOR_PATTERN` 모양만 구분하면 된다.
 */

export type AnchorPart = {
  type: "anchor";
  kind: "wiki" | "source";
  alias: string;
  id?: string;
};

export type TextPart = { type: "text"; value: string };

export type ResolvedAnchor = { alias: string; kind: string; id: string };

// D-04 / CITE-01~03 — 이 서버가 이번 요청에서 실제로 발급하는 형태만 매치한다.
// nexuswiki_core/citations.py의 ISSUED_ANCHOR_PATTERN과 문자 단위로 동일해야
// 한다 — 어느 한쪽만 바뀌면 클라이언트/서버가 서로 다른 앵커 모양을 인식하게
// 된다(citation-anchors.test.ts의 drift guard가 이 동등성을 계속 검사한다).
export const ISSUED_ANCHOR_PATTERN = /\[\[(wiki:w\d+|src:s\d+)\]\]/g;

/**
 * `text`를 text/anchor part로 분리한다.
 *
 * - `resolved`가 `undefined`이면 스트리밍 모드다: 아직 어떤 앵커가 실제 발급된
 *   것인지 알 수 없으므로, 앵커 모양 토큰은 전부(장차 위조로 밝혀질 것까지
 *   포함해) 동일한 비활성 anchor part로 emit한다 — T-06-18: 위조 앵커가
 *   해소되기 전까지 실제 링크처럼 보이는 순간이 없어야 한다.
 * - `resolved`가 주어지면(citations 이벤트 도착 후) 별칭이 발급 맵에 없는
 *   앵커는 `resolve_citations()`의 `_strip_fabricated`와 동일하게 아무 part도
 *   emit하지 않고 조용히 사라진다.
 */
export function splitTextWithAnchors(
  text: string,
  resolved?: ResolvedAnchor[],
): (TextPart | AnchorPart)[] {
  const resolvedByAlias =
    resolved === undefined
      ? undefined
      : new Map(resolved.map((entry) => [entry.alias, entry]));

  const parts: (TextPart | AnchorPart)[] = [];
  let lastIndex = 0;

  // matchAll은 (ISSUED_ANCHOR_PATTERN이 /g라도) 내부적으로 정규식을 복제해
  // 순회하므로 이 모듈 상수의 lastIndex를 오염시키지 않는다.
  for (const match of text.matchAll(ISSUED_ANCHOR_PATTERN)) {
    const matchIndex = match.index ?? 0;
    if (matchIndex > lastIndex) {
      parts.push({ type: "text", value: text.slice(lastIndex, matchIndex) });
    }

    const token = match[1]; // 예: "wiki:w1" 또는 "src:s1"
    const [prefix, alias] = token.split(":");
    const kind: AnchorPart["kind"] = prefix === "wiki" ? "wiki" : "source";

    if (resolvedByAlias === undefined) {
      parts.push({ type: "anchor", kind, alias });
    } else {
      const hit = resolvedByAlias.get(alias);
      if (hit) {
        parts.push({ type: "anchor", kind, alias, id: hit.id });
      }
      // else: 위조(파싱은 됐지만 이 요청이 발급하지 않음) — 아무것도 emit하지 않는다.
    }

    lastIndex = matchIndex + match[0].length;
  }

  if (lastIndex < text.length) {
    parts.push({ type: "text", value: text.slice(lastIndex) });
  }

  if (parts.length === 0) {
    parts.push({ type: "text", value: text });
  }

  return parts;
}

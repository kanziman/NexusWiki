import { describe, expect, it } from "vitest";

import {
  ISSUED_ANCHOR_PATTERN,
  splitTextWithAnchors,
} from "@/lib/citation-anchors";

describe("citation-anchors", () => {
  it("ISSUED_ANCHOR_PATTERN은 nexuswiki_core/citations.py의 정규식과 문자 단위로 동일하다 (drift guard)", () => {
    expect(ISSUED_ANCHOR_PATTERN.source).toBe(
      "\\[\\[(wiki:w\\d+|src:s\\d+)\\]\\]",
    );
  });

  it("해소 맵 없이(스트리밍 모드) 앵커 모양 토큰을 전부 비활성 placeholder로 분리한다", () => {
    const text = "본문 [[src:s1]] 계속 [[wiki:w2]] 끝";
    const parts = splitTextWithAnchors(text);

    expect(parts).toEqual([
      { type: "text", value: "본문 " },
      { type: "anchor", kind: "source", alias: "s1" },
      { type: "text", value: " 계속 " },
      { type: "anchor", kind: "wiki", alias: "w2" },
      { type: "text", value: " 끝" },
    ]);
  });

  it("해소 맵이 주어지면 발급되지 않은(위조) 별칭은 렌더 결과에서 완전히 사라진다", () => {
    const text = "본문 [[src:s1]] 계속 [[wiki:w9]] 끝";
    const resolved = [{ alias: "s1", kind: "source", id: "uuid-1" }];
    const parts = splitTextWithAnchors(text, resolved);

    // w9는 발급 맵(resolved)에 없으므로 placeholder조차 남기지 않는다 —
    // resolve_citations()의 strip-not-render 동작과 동일하다.
    expect(parts).toEqual([
      { type: "text", value: "본문 " },
      { type: "anchor", kind: "source", alias: "s1", id: "uuid-1" },
      { type: "text", value: " 계속 " },
      { type: "text", value: " 끝" },
    ]);
  });

  it("혼합 한국어/영어 텍스트에서 정상 앵커 2개는 각각 {kind, alias, id}를 alternating text/anchor로 싣는다", () => {
    const text = "Answer: [[wiki:w1]] and 근거는 [[src:s2]] 입니다";
    const resolved = [
      { alias: "w1", kind: "wiki", id: "wiki-uuid" },
      { alias: "s2", kind: "source", id: "chunk-uuid" },
    ];
    const parts = splitTextWithAnchors(text, resolved);

    expect(parts).toEqual([
      { type: "text", value: "Answer: " },
      { type: "anchor", kind: "wiki", alias: "w1", id: "wiki-uuid" },
      { type: "text", value: " and 근거는 " },
      { type: "anchor", kind: "source", alias: "s2", id: "chunk-uuid" },
      { type: "text", value: " 입니다" },
    ]);
  });

  it("앵커가 하나도 없는 텍스트는 단일 text part로 변경 없이 돌아온다", () => {
    const text = "이것은 앵커가 없는 평범한 텍스트입니다.";
    const parts = splitTextWithAnchors(text);

    expect(parts).toEqual([{ type: "text", value: text }]);
  });
});

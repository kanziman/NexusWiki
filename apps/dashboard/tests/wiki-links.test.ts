import { describe, expect, it } from "vitest";

import { baseSlug, resolveWikiLinks } from "@/lib/wiki-links";

describe("wiki-links", () => {
  // packages/core/src/nexuswiki_core/slug.py._base_slug의 실제 출력과 대조한
  // 픽스처 3종 (06-07-PLAN.md Task 1 behavior-spec) — 세션 중
  // `uv run python3 -c "from nexuswiki_core.slug import _base_slug; ..."`로
  // 직접 실측한 값이다.
  describe("baseSlug", () => {
    it("한국어 제목을 Python _base_slug와 동일하게 슬러그화한다", () => {
      expect(baseSlug("한국어 제목입니다")).toBe("한국어-제목입니다");
    });

    it("구두점 섞인 영어 제목을 Python _base_slug와 동일하게 슬러그화한다", () => {
      expect(baseSlug("Hello, World! Title.")).toBe("hello-world-title");
    });

    it("한글/영어/숫자가 섞인 제목을 Python _base_slug와 동일하게 슬러그화한다", () => {
      expect(baseSlug("Mixed 한글과 English 123")).toBe(
        "mixed-한글과-english-123",
      );
    });

    it("빈 문자열/전부 비허용 문자 입력은 결정적이고 비어있지 않은 폴백을 반환한다", () => {
      const empty = baseSlug("");
      const punctOnly = baseSlug("!!!");

      expect(empty.length).toBeGreaterThan(0);
      expect(punctOnly.length).toBeGreaterThan(0);
      // 결정적 — 같은 입력은 항상 같은 폴백을 낸다.
      expect(baseSlug("")).toBe(empty);
      expect(baseSlug("!!!")).toBe(punctOnly);
    });
  });

  describe("resolveWikiLinks", () => {
    it("resolved:true 행과 매치되는 [[제목]]을 해소된 link part로 만든다", () => {
      const content = "본문 [[주제 A]] 계속";
      const links = [{ target_slug: baseSlug("주제 A"), resolved: true }];

      expect(resolveWikiLinks(content, links)).toEqual([
        { type: "text", value: "본문 " },
        {
          type: "link",
          title: "주제 A",
          resolved: true,
          slug: baseSlug("주제 A"),
        },
        { type: "text", value: " 계속" },
      ]);
    });

    it("resolved:false 행과 매치되는 [[제목]]을 미해결 link part로 만든다", () => {
      const content = "[[주제 B]]";
      const links = [{ target_slug: baseSlug("주제 B"), resolved: false }];

      expect(resolveWikiLinks(content, links)).toEqual([
        {
          type: "link",
          title: "주제 B",
          resolved: false,
          slug: baseSlug("주제 B"),
        },
      ]);
    });

    it("links에 전혀 없는 [[제목]]도 계산된 slug를 실은 미해결 link part가 된다", () => {
      const content = "[[아직 없는 페이지]]";

      expect(resolveWikiLinks(content, [])).toEqual([
        {
          type: "link",
          title: "아직 없는 페이지",
          resolved: false,
          slug: baseSlug("아직 없는 페이지"),
        },
      ]);
    });

    it("본문 [[주제 A]] 계속 [[주제 B]] 끝 형태에서 순서 있는 text/link part 배열을 만든다", () => {
      const content = "본문 [[주제 A]] 계속 [[주제 B]] 끝";
      const links = [
        { target_slug: baseSlug("주제 A"), resolved: true },
        { target_slug: baseSlug("주제 B"), resolved: false },
      ];

      expect(resolveWikiLinks(content, links)).toEqual([
        { type: "text", value: "본문 " },
        {
          type: "link",
          title: "주제 A",
          resolved: true,
          slug: baseSlug("주제 A"),
        },
        { type: "text", value: " 계속 " },
        {
          type: "link",
          title: "주제 B",
          resolved: false,
          slug: baseSlug("주제 B"),
        },
        { type: "text", value: " 끝" },
      ]);
    });

    it("[[...]] 매치가 하나도 없는 content는 변경 없이 단일 text part로 돌아온다", () => {
      const content = "이것은 WikiLink가 없는 평범한 본문입니다.";

      expect(resolveWikiLinks(content, [])).toEqual([
        { type: "text", value: content },
      ]);
    });
  });
});

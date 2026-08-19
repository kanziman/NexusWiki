import { describe, expect, it } from "vitest";

import {
  baseSlug,
  firstWikiLinkExcerpt,
  firstWikiLinkSpelling,
  resolveWikiLinks,
} from "@/lib/wiki-links";

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

  describe("firstWikiLinkSpelling", () => {
    it("targetSlug로 슬러그화되는 첫 [[표기]]를 원문 그대로 반환한다", () => {
      const content = "본문 [[캐시 계층 전략]] 이어지는 설명";

      expect(firstWikiLinkSpelling(content, baseSlug("캐시 계층 전략"))).toBe(
        "캐시 계층 전략",
      );
    });

    it("같은 링크가 여러 번 나오면 첫 등장의 표기만 쓴다", () => {
      const content = "[[RLS 정책(v2)]] ... 나중에 다시 [[rls 정책(v2)]]";

      expect(firstWikiLinkSpelling(content, baseSlug("RLS 정책(v2)"))).toBe(
        "RLS 정책(v2)",
      );
    });

    it("targetSlug와 매치되는 [[...]]가 없으면 null을 반환한다", () => {
      const content = "[[다른 주제]] 뿐인 본문";

      expect(firstWikiLinkSpelling(content, baseSlug("찾는 주제"))).toBeNull();
    });

    it("[[...]] 자체가 없는 본문에서는 null을 반환한다", () => {
      expect(
        firstWikiLinkSpelling("WikiLink가 없다", baseSlug("아무거나")),
      ).toBeNull();
    });
  });

  describe("firstWikiLinkExcerpt", () => {
    it("링크 앞뒤로 짧은 본문은 잘리지 않고 말줄임도 붙지 않는다", () => {
      const content = "앞 문장. [[캐시 계층 전략]] 뒤 문장.";

      expect(
        firstWikiLinkExcerpt(content, baseSlug("캐시 계층 전략"), 80),
      ).toBe("앞 문장. 캐시 계층 전략 뒤 문장.");
    });

    it("window 밖으로 잘린 쪽에만 말줄임표를 붙인다", () => {
      const before = "가".repeat(200);
      const after = "나".repeat(200);
      const content = `${before}[[주제]]${after}`;

      const excerpt = firstWikiLinkExcerpt(content, baseSlug("주제"), 10);

      expect(excerpt).not.toBeNull();
      expect(excerpt!.startsWith("…")).toBe(true);
      expect(excerpt!.endsWith("…")).toBe(true);
      expect(excerpt).toContain("주제");
    });

    it("한 문서에 같은 링크가 여러 번 나오면 첫 등장 주변만 발췌한다", () => {
      const content =
        "첫 등장 근처 문맥 [[반복 주제]] 여기까지. 한참 뒤에 " +
        "두번째 등장 근처 문맥 [[반복 주제]] 여기까지.";

      const excerpt = firstWikiLinkExcerpt(content, baseSlug("반복 주제"), 20);

      expect(excerpt).toContain("첫 등장 근처");
      expect(excerpt).not.toContain("두번째 등장 근처");
    });

    it("발췌 window 안에 다른 [[...]]가 섞여 있으면 브래킷 없이 평문으로 펼친다", () => {
      const content = "관련 개념은 [[다른 개념]]이다. 여기 [[대상 주제]] 설명.";

      const excerpt = firstWikiLinkExcerpt(content, baseSlug("대상 주제"), 40);

      expect(excerpt).not.toBeNull();
      expect(excerpt).toContain("다른 개념");
      expect(excerpt).not.toContain("[[");
      expect(excerpt).not.toContain("]]");
    });

    it("targetSlug와 매치되는 [[...]]가 없으면 null을 반환한다", () => {
      expect(
        firstWikiLinkExcerpt("[[다른 주제]] 뿐", baseSlug("찾는 주제")),
      ).toBeNull();
    });
  });
});

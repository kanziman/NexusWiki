import { describe, expect, it } from "vitest";

import {
  cleanWikiContent,
  estimateReadMinutes,
  extractHeadings,
  plainCitationSnippet,
  publicWikiPath,
  workspaceInitials,
} from "@/lib/wiki-document";

describe("wiki-document", () => {
  it("strips the trailing related-documents markdown section", () => {
    const raw = `## 핵심 개념
설명입니다.

## 관련 문서
- [[데이터-계층]]
`;
    expect(cleanWikiContent(raw)).toBe("## 핵심 개념\n설명입니다.");
    expect(extractHeadings(cleanWikiContent(raw)).map((h) => h.title)).toEqual([
      "핵심 개념",
    ]);
  });

  it("strips a trailing '관련 문서:' wiki-link row as well as a heading section", () => {
    const raw = `## 검증 계획
표입니다.

관련 문서: [[데이터-계층]] , [[시스템-아키텍처]] , [[hybrid-retrieval]]
`;
    expect(cleanWikiContent(raw)).toBe("## 검증 계획\n표입니다.");
  });

  it("folds markdown headings and emphasis out of citation snippets and appends ellipsis when exceeding maxChars", () => {
    const raw = `# background-job-lifecycle Specification
## Purpose
장시간 수집이 **at-least-once** 로 끝나야 한다.
`;
    expect(plainCitationSnippet(raw)).toBe(
      "background-job-lifecycle Specification\nPurpose\n장시간 수집이 at-least-once 로 끝나야 한다.",
    );
    expect(
      plainCitationSnippet(
        "# background-job-lifecycle Specification ## Purpose 장시간 수집이 **at-least-once** 로 끝나야 한다.",
      ),
    ).not.toContain("##");
    expect(plainCitationSnippet(raw)).not.toContain("**");
    expect(plainCitationSnippet(raw)).not.toContain("##");
    expect(plainCitationSnippet("가".repeat(100), 50)).toBe(
      `${"가".repeat(50)}…`,
    );
  });

  it("공개 경로·읽기 시간·이니셜을 사이드카 표시용으로 계산한다", () => {
    expect(publicWikiPath("nexuswiki", "background-job-lifecycle")).toBe(
      "/p/nexuswiki/background-job-lifecycle",
    );
    expect(estimateReadMinutes("")).toBe(1);
    expect(estimateReadMinutes("가".repeat(800))).toBe(2);
    expect(workspaceInitials("엔지니어링 팀")).toBe("엔지");
  });
});

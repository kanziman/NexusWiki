import { render } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { KnowledgeGrid } from "@/components/KnowledgeGrid";
import { WikiLibrary } from "@/components/WikiLibrary";
import { isVerified, verificationLabel } from "@/lib/verification-label";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => "/w/ws-1/wiki",
  useSearchParams: () => new URLSearchParams(),
}));

/**
 * dashboard-design-consistency 「Shared state and control language」의
 * 시나리오 "Member sees the same underlying status on two destinations" 를
 * 지키는 테스트.
 *
 * ⚠️ 단위 함수만 검증하면 이 계약이 지켜지지 않는다. 실제로 갈라졌던 방식은
 * 매핑 함수가 틀린 게 아니라 **컴포넌트가 함수를 안 쓰고 자기 문자열을 들고
 * 있던 것**이었다. 그래서 두 목적지를 실제로 렌더해 같은 라벨이 나오는지 본다.
 */
describe("검증 상태 어휘", () => {
  const verifiedPage = {
    id: "page-1",
    slug: "tenant-isolation",
    title: "테넌트 격리 아키텍처",
    category: "concepts",
    verification_status: "verified",
  };

  it("같은 verified 문서가 홈 대시보드와 위키 라이브러리에서 같은 라벨로 표시된다", () => {
    const expected = verificationLabel(verifiedPage);
    const docId = `wiki-document-${verifiedPage.slug}`;

    // 두 목적지의 마크업이 다르다 — 홈은 라벨을 <b class="badge">에 따로 담고,
    // 라이브러리는 카테고리와 한 <span>에 합친다("개념 · 검증됨"). 그래서
    // 정확 일치가 아니라 문서 항목 전체 텍스트에 라벨이 들어있는지로 본다.
    const home = render(
      <KnowledgeGrid
        workspaceId="ws-1"
        wikiPages={[{ ...verifiedPage, citation_count: 3 }]}
        backlogItems={[]}
      />,
    );
    expect(
      document.querySelector(`[data-od-id="${docId}"]`)?.textContent,
    ).toContain(expected);
    home.unmount();

    render(
      <WikiLibrary
        workspaceId="ws-1"
        pages={[{ ...verifiedPage, content: "본문", disputed: false }]}
      />,
    );
    expect(
      document.querySelector(`[data-od-id="${docId}"]`)?.textContent,
    ).toContain(expected);
  });

  it("충돌 문서도 두 목적지에서 같은 라벨로 표시된다", () => {
    // ⚠️ 회귀 방지. verified 만 통일하고 disputed 를 놓쳤던 적이 있다 —
    // 홈 대시보드가 disputed 를 select 하지도 타입에 갖지도 않아, 충돌
    // 문서가 라이브러리에서는 "충돌 감지"인데 홈에서는 "검증됨"이었다.
    // 순수 함수만 검증하면 이 부류는 절대 잡히지 않는다.
    const disputedPage = { ...verifiedPage, disputed: true };
    const expected = verificationLabel(disputedPage);
    expect(expected).toBe("충돌 감지");
    const docId = `wiki-document-${verifiedPage.slug}`;

    const home = render(
      <KnowledgeGrid
        workspaceId="ws-1"
        wikiPages={[disputedPage]}
        backlogItems={[]}
      />,
    );
    expect(
      document.querySelector(`[data-od-id="${docId}"]`)?.textContent,
    ).toContain(expected);
    home.unmount();

    render(
      <WikiLibrary
        workspaceId="ws-1"
        pages={[{ ...disputedPage, content: "본문" }]}
      />,
    );
    expect(
      document.querySelector(`[data-od-id="${docId}"]`)?.textContent,
    ).toContain(expected);
  });

  it("disputed는 검증 단계보다 먼저 표시된다", () => {
    // 충돌은 "얼마나 검증됐는가"보다 먼저 해소해야 하는 상태다.
    expect(
      verificationLabel({ verification_status: "verified", disputed: true }),
    ).toBe("충돌 감지");
    expect(
      isVerified({ verification_status: "verified", disputed: true }),
    ).toBe(false);
  });

  it("만료된 검증은 검증으로 세지 않고 만료로 표시한다", () => {
    // 0007_search_and_queue_extensions.sql §5: "만료된 검증을 검증으로 세면
    // 오래된 위키가 영원히 verified 로 남습니다." 리더만 만료를 알고 목록은
    // "검증됨"이던 상태가 실제로 있었다.
    const expired = {
      verification_status: "verified",
      expires_at: "2020-01-01T00:00:00Z",
    };
    expect(verificationLabel(expired)).toBe("검증 만료됨");
    expect(isVerified(expired)).toBe(false);

    const live = {
      verification_status: "verified",
      expires_at: "2999-01-01T00:00:00Z",
    };
    expect(verificationLabel(live)).toBe("검증됨");
    expect(isVerified(live)).toBe(true);

    // expires_at 이 없으면 만료 개념이 없는 것으로 본다.
    expect(isVerified({ verification_status: "verified" })).toBe(true);
  });

  it("만료 문서도 홈에서 무표시로 지나가지 않는다", () => {
    const docId = `wiki-document-${verifiedPage.slug}`;
    const expiredPage = {
      ...verifiedPage,
      expires_at: "2020-01-01T00:00:00Z",
    };

    render(
      <KnowledgeGrid
        workspaceId="ws-1"
        wikiPages={[expiredPage]}
        backlogItems={[]}
      />,
    );

    const row = document.querySelector(`[data-od-id="${docId}"]`);
    expect(row?.textContent).toContain("검증 만료됨");
    // .badge.verified 는 살아있는 검증에만 쓴다(workspace-home-prd.md §3.3).
    expect(row?.querySelector(".badge.verified")).toBeNull();
  });

  it("알 수 없는 상태값이 화면에 원시 enum으로 새지 않는다", () => {
    expect(verificationLabel({ verification_status: "banana" })).toBe(
      "검증 필요",
    );
    expect(verificationLabel({})).toBe("검증 필요");
  });
});

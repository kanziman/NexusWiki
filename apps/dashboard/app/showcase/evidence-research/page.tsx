import type { Metadata } from "next";
import { redirect } from "next/navigation";

// 기존 공개 주소를 통합 사례로 연결한다. JSON 다운로드 주소는 유지한다.
export const dynamic = "force-static";
export const metadata: Metadata = {
  title: "재검색은 답을 더 찾았을까? | NexusWiki",
  description:
    "같은 문서·모델·검색 정책에서 측정한 도구 재검색의 품질, 비용, 지연 비교.",
};

export default function EvidenceResearchPage() {
  redirect("/showcase/evaluation#research");
}

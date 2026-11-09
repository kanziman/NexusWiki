import type { Metadata } from "next";

import {
  EvidenceResearchShowcase,
  type ResearchEvaluation,
} from "@/components/EvidenceResearchShowcase";
import evaluation from "@/content/evidence-research.json";

// 합성 평가 사본만 정적으로 읽는다. 운영 클라이언트를 이 경계에 넣지 않는다.
export const dynamic = "force-static";
export const metadata: Metadata = {
  title: "재검색은 답을 더 찾았을까? | NexusWiki",
  description:
    "같은 문서·모델·검색 정책에서 측정한 도구 재검색의 품질, 비용, 지연 비교.",
};

export default function EvidenceResearchPage() {
  return (
    <EvidenceResearchShowcase
      evaluation={evaluation as unknown as ResearchEvaluation}
    />
  );
}

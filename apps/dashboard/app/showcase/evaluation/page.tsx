import type { Metadata } from "next";

import type { EvaluationRecord } from "@/components/EvaluationShowcase";
import record from "@/content/evaluation.json";
import controlled from "@/content/controlled-ai/step1.json";
import research from "@/content/evidence-research.json";
import { AiEngineeringShowcase } from "@/components/AiEngineeringShowcase";
import type { ControlledAiEvidence } from "@/components/ControlledAiShowcase";
import type { ResearchEvaluation } from "@/components/EvidenceResearchShowcase";

// 커밋된 허용 필드 공개 기록만 정적으로 읽는다. 운영 클라이언트를 이 경계에 넣지 않는다.
export const dynamic = "force-static";
export const metadata: Metadata = {
  title: "AI를 평가하고, 통제하고, 도입을 판단한 기록 | NexusWiki",
  description:
    "채점 기준 검증부터 실패 통제, 재검색 OFF/ON 실험과 도입 판단까지. NexusWiki의 AI 엔지니어링 사례와 근거를 한 페이지에서 확인합니다.",
};

export default function EvaluationPage() {
  return (
    <AiEngineeringShowcase
      record={record as unknown as EvaluationRecord}
      controlled={controlled as ControlledAiEvidence}
      research={research as unknown as ResearchEvaluation}
    />
  );
}

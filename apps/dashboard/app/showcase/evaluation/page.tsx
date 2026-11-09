import type { Metadata } from "next";

import {
  EvaluationShowcase,
  type EvaluationRecord,
} from "@/components/EvaluationShowcase";
import record from "@/content/evaluation.json";

// 커밋된 허용 필드 공개 기록만 정적으로 읽는다. 운영 클라이언트를 이 경계에 넣지 않는다.
export const dynamic = "force-static";
export const metadata: Metadata = {
  title: "Ask 답변 품질을 무엇으로 쟀나 | NexusWiki",
  description:
    "합성 샘플에서 같은 조건으로 반복 측정한 Ask 답변 통과 · 거절 성능과 재현 조건, 한계.",
};

export default function EvaluationPage() {
  return <EvaluationShowcase record={record as unknown as EvaluationRecord} />;
}

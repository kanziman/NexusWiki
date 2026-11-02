import type { Metadata } from "next";

import {
  ControlledAiShowcase,
  type ControlledAiEvidence,
} from "@/components/ControlledAiShowcase";
import evidence from "@/content/controlled-ai/step1.json";

/**
 * 공개 쇼케이스 라우트 (#168).
 *
 * 설계 근거: openspec/changes/ai-control-flow-accounting/design.md > D10
 *
 * ⚠️ 저장소에 커밋된 합성 증거만 빌드 시점에 읽는다. Supabase나 API 클라이언트를 여기서 import하면
 * 실제 테넌트 데이터가 공개 화면으로 나갈 경로가 생긴다. `tests/ControlledAiShowcase.test.tsx`가
 * 이 파일과 컴포넌트의 import를 검사한다. 쿠키를 읽지 않으므로 세션이 있는 방문자도 같은 내용을 본다.
 */
export const dynamic = "force-static";

export const metadata: Metadata = {
  title: "Controlled AI 전후 비교 | NexusWiki",
  description:
    "합성 시나리오로 측정한 NexusWiki의 AI 통제 전후 동작을 보여줍니다.",
};

export default function ControlledAiShowcasePage() {
  return <ControlledAiShowcase evidence={evidence as ControlledAiEvidence} />;
}

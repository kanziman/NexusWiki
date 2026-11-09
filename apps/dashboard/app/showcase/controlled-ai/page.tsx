import type { Metadata } from "next";
import { redirect } from "next/navigation";

/**
 * 기존 공개 주소는 통합 사례의 통제 구역으로 연결한다.
 * 세션이나 운영 데이터 없이 같은 페이지 안에서 모든 증거를 확인한다.
 */
export const dynamic = "force-static";

export const metadata: Metadata = {
  title: "Controlled AI 전후 비교 | NexusWiki",
  description:
    "합성 시나리오로 측정한 NexusWiki의 AI 통제 전후 동작을 보여줍니다.",
};

export default function ControlledAiShowcasePage() {
  redirect("/showcase/evaluation#control");
}

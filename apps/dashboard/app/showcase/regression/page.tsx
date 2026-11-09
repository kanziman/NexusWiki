import type { Metadata } from "next";
import { RegressionDashboard } from "@/components/RegressionDashboard";

// 운영 데이터·모델 호출 없이 공개 합성 실행으로 동작하는 독립 작업대다.
export const dynamic = "force-static";
export const metadata: Metadata = {
  title: "회귀 분석 작업대 | NexusWiki",
  description:
    "평가 실행을 비교하고 문항별 개선과 회귀, 비용과 지연을 분석하는 작업대.",
};
export default function RegressionPage() {
  return <RegressionDashboard />;
}

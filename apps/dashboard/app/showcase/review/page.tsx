import type { Metadata } from "next";
import { GoldenReviewPage } from "@/components/GoldenReviewPage";

export const metadata: Metadata = { title: "사람 검토 작업대 | NexusWiki" };

export default function ReviewPage() {
  return <GoldenReviewPage />;
}

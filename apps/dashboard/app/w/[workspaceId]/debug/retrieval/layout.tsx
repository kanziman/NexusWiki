import { notFound } from "next/navigation";
import type { ReactNode } from "react";

export const metadata = {
  robots: { index: false, follow: false },
};

// 구현 추적: openspec/changes/retrieval-debug-viewer
export default function RetrievalDebugLayout({
  children,
}: {
  children: ReactNode;
}) {
  // 배포 환경에서 요청 자체를 막아야 실제 워크스페이스 검색이 디버그 화면을
  // 통해 실행되는 우회 경로가 생기지 않는다(design.md Decision 1·2).
  if (process.env.NODE_ENV !== "development") {
    notFound();
  }

  return children;
}

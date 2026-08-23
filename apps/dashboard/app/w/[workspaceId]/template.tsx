"use client";

import type { ReactNode } from "react";

/**
 * Next.js App Router 템플릿 — 레이아웃과 달리 라우트가 바뀔 때마다
 * 새로운 인스턴스가 마운트되므로 부드러운 페이지 전환 애니메이션을 보장한다.
 */
export default function WorkspaceTemplate({
  children,
}: {
  children: ReactNode;
}) {
  return <div className="workspace-page-transition">{children}</div>;
}

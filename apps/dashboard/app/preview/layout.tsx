import { notFound } from "next/navigation";
import type { ReactNode } from "react";

export const metadata = {
  robots: { index: false, follow: false },
};

export default function PreviewLayout({ children }: { children: ReactNode }) {
  // 이 경계가 없으면 fixture만 쓰더라도 배포 번들에서 `/preview`가 공개된다.
  // middleware matcher와 독립적으로 전체 하위 경로를 막아야 matcher 변경 때
  // mock 화면만 남는 우회 경로가 생기지 않는다.
  if (process.env.NODE_ENV !== "development") {
    notFound();
  }

  return children;
}

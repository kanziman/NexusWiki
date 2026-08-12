import type { Metadata } from "next";
import { Inter } from "next/font/google";
import type { ReactNode } from "react";

import "./globals.css";

// Airbnb Cereal/Circular(design-tokens.css --font-family-base)은 라이선스가
// 없는 상용 서체라 이 프로젝트에서 쓸 수 없다 — Inter로 대체(06-UI-SPEC.md
// Design System 표 근거). --font-inter 변수를 globals.css의 @theme이
// --font-family-base 슬롯에 매핑한다(06-01 Task 2).
const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
});

export const metadata: Metadata = {
  title: "NexusWiki",
  description: "출처까지 추적할 수 있는 살아 있는 위키",
};

export default function RootLayout({
  children,
}: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="ko" className={inter.variable}>
      <body>{children}</body>
    </html>
  );
}

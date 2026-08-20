import type { Metadata } from "next";
import { Inter, JetBrains_Mono, Plus_Jakarta_Sans } from "next/font/google";
import localFont from "next/font/local";
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

// v2 디자인 시스템(nexuswiki-design-system.css)의 --font-display/--font-body/
// --font-mono가 가리키는 실제 서체 3종. 프로토타입 HTML은 Google Fonts
// <link>로 이 중 둘(Plus Jakarta Sans, JetBrains Mono)만 불러오고
// Pretendard는 아무 데서도 로드하지 않는다 — self-host로 통일한다.
//
// weight는 프로토타입 <link>가 아니라 nexuswiki-design-system.css의 실제
// var(--font-display)/var(--font-mono) 사용처를 센 값이다 — 둘이 어긋난다.
// display는 29곳 전부 800(예외 1곳은 strong 기본 bolder→700)이라 600은
// 아무도 안 쓴다. mono는 500·600·700·800이 전부 쓰이는데 프로토타입
// <link>는 500·600만 요청해 700/800 사용처(.stat b, .budget-amount 등)가
// 로드 안 된 굵기로 폴백하고 있었다.
const jakarta = Plus_Jakarta_Sans({
  subsets: ["latin"],
  weight: ["700", "800"],
  variable: "--font-jakarta",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  weight: ["500", "600", "700", "800"],
  variable: "--font-jetbrains-mono",
});

// Pretendard는 Google Fonts에 없다 — npm pretendard 패키지(SIL OFL)의 가변
// 폰트 파일을 next/font/local로 self-host한다.
const pretendard = localFont({
  src: "../node_modules/pretendard/dist/web/variable/woff2/PretendardVariable.woff2",
  variable: "--font-pretendard",
  weight: "45 920",
});

export const metadata: Metadata = {
  title: "NexusWiki",
  description: "출처까지 추적할 수 있는 살아 있는 위키",
};

export default function RootLayout({
  children,
}: Readonly<{ children: ReactNode }>) {
  return (
    <html
      lang="ko"
      className={`${inter.variable} ${jakarta.variable} ${jetbrainsMono.variable} ${pretendard.variable}`}
    >
      <body>{children}</body>
    </html>
  );
}

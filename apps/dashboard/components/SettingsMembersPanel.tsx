"use client";

import { useState } from "react";

import { InviteForm } from "@/components/InviteForm";
import { MembersList } from "@/components/MembersList";

export type SettingsMembersPanelProps = {
  workspaceId: string;
  currentUserId: string;
};

// [Rule 3 - Blocking] MembersList와 InviteForm 사이의 "초대 성공 시 목록을
// 갱신할 방법을 준다"는 연결(06-03-PLAN.md Task 3 <behavior>)은 두 컴포넌트
// 위에서 state를 들고 있을 클라이언트 컴포넌트가 필요하다. settings/page.tsx는
// 플랜이 명시한 Server Component라 자체 state를 가질 수 없으므로, 이 얇은
// 클라이언트 래퍼가 refreshToken을 key로 넘겨 초대 성공 시 MembersList를
// 리마운트시킨다(key-remount 방식, Task 3 "component's choice" 중 선택) —
// 06-01의 누락된 page.tsx 추가, 06-02의 jsdom 폴리필 추가와 같은 계열의,
// 플랜 자신의 <done> 기준을 만족시키기 위해 필요한 최소 추가다.
export function SettingsMembersPanel({
  workspaceId,
  currentUserId,
}: SettingsMembersPanelProps) {
  const [refreshToken, setRefreshToken] = useState(0);

  return (
    // [Rule 1 - Bug] Tailwind의 max-w-xl 유틸리티를 쓰지 않는다 — 이 프로젝트의
    // globals.css @theme이 --spacing-xl(32px)만 정의하고 --container-xl은
    // 정의하지 않아, 컴파일된 CSS에서 max-w-xl이 --spacing-xl(32px)로
    // 잘못 해석되는 것을 실측으로 확인했다(Playwright getComputedStyle,
    // maxWidth: "32px"). 640px 고정값을 인라인 style로 직접 지정한다 —
    // LoginForm.tsx/NavShell.tsx가 @theme에 없는 토큰(font 축약형 등)에
    // 인라인 style을 쓰는 것과 같은 패턴.
    <div className="flex flex-col gap-xl" style={{ maxWidth: "640px" }}>
      <section className="flex flex-col gap-base">
        <h2 className="text-ink" style={{ font: "var(--font-title-md)" }}>
          멤버
        </h2>
        <MembersList
          key={refreshToken}
          workspaceId={workspaceId}
          currentUserId={currentUserId}
        />
      </section>

      <section className="flex flex-col gap-base">
        <h2 className="text-ink" style={{ font: "var(--font-title-md)" }}>
          멤버 초대
        </h2>
        <InviteForm
          workspaceId={workspaceId}
          onInvited={() => setRefreshToken((token) => token + 1)}
        />
      </section>
    </div>
  );
}

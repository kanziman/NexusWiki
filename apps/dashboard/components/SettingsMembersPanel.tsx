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
    <div className="flex max-w-xl flex-col gap-xl">
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

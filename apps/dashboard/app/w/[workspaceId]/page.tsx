// 워크스페이스 홈의 실제 콘텐츠(드롭존/Ask/위키 등)는 이후 Phase 6 플랜의 몫이다
// (06-02+, depends_on: ["06-01"]). 이 파일은 `app/w/[workspaceId]/layout.tsx`가
// 렌더링될 라우트 세그먼트를 성립시키기 위한 최소 placeholder — layout.tsx 없이는
// Next.js App Router가 `/w/[workspaceId]`를 매칭할 page.tsx를 찾지 못해 404가 된다.
export default function WorkspaceHomePage() {
  return (
    <p style={{ font: "var(--font-body-md)", color: "var(--color-body)" }}>
      워크스페이스 대시보드는 다음 플랜에서 채워집니다.
    </p>
  );
}

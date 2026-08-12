import { GraphCanvas } from "@/components/GraphCanvas";
import { GraphLensFilter } from "@/components/GraphLensFilter";

type GraphPageProps = {
  params: Promise<{ workspaceId: string }>;
  searchParams: Promise<{ category?: string }>;
};

// UI-06 그래프 캔버스 라우트. 이 페이지 자신은 데이터를 조회하지 않는다 —
// GraphCanvas.tsx가 클라이언트에서 직접 fetch하므로, ?category= 재선택마다
// 서버 왕복/RSC 재요청 없이 재조회된다(Task 3 <action>, Phase 6의 다른
// 표면이 전부 서버 사이드 1차 fetch를 쓰는 것과 의도적으로 다른 지점).
export default async function GraphPage({
  params,
  searchParams,
}: GraphPageProps) {
  const { workspaceId } = await params;
  const { category } = await searchParams;
  const activeCategory = category ?? null;

  return (
    <div className="flex flex-col gap-base">
      <GraphLensFilter
        workspaceId={workspaceId}
        activeCategory={activeCategory}
      />
      <GraphCanvas workspaceId={workspaceId} category={activeCategory} />
    </div>
  );
}

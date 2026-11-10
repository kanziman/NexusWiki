import record from "@/content/experiments.json";

export const dynamic = "force-static";

// 페이지가 렌더링에 쓴 것과 같은 실험 스냅샷을 그대로 내려준다.
export function GET() {
  return Response.json(record, {
    headers: {
      "Content-Disposition": 'attachment; filename="eval-experiments.v1.json"',
    },
  });
}

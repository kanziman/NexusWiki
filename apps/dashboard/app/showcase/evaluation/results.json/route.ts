import record from "@/content/evaluation.json";

export const dynamic = "force-static";

// 페이지가 렌더링에 쓴 것과 같은 공개 기록을 그대로 내려준다.
export function GET() {
  return Response.json(record, {
    headers: {
      "Content-Disposition": 'attachment; filename="evaluation.v1.json"',
    },
  });
}

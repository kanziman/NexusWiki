import records from "@/content/evaluation-runs.json";

// 합성 실행의 허용 필드 사본만 내려준다. 운영 데이터 경로를 추가하지 않는다.
export const dynamic = "force-static";
export function GET() {
  return Response.json(records, {
    headers: {
      "Content-Disposition": 'attachment; filename="evaluation-runs.json"',
    },
  });
}

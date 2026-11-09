import evaluation from "@/content/evidence-research.json";

export const dynamic = "force-static";

export function GET() {
  return Response.json(evaluation, {
    headers: {
      "Content-Disposition": 'attachment; filename="evidence-research.v1.json"',
    },
  });
}

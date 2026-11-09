import { readFile } from "node:fs/promises";
import { resolve } from "node:path";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

/** 개발 서버를 루프백에 바인딩했을 때만 쓰는 로컬 실행기 프록시. 운영 빌드에서는 항상 거부한다. */
function allowed(request: Request) {
  if (process.env.NODE_ENV !== "development") return false;
  if (process.env.LOCAL_EVALUATION_ENABLED !== "1") return false;
  const url = new URL(request.url);
  if (!["127.0.0.1", "localhost", "[::1]"].includes(url.hostname)) return false;
  const host = request.headers.get("host") ?? url.host;
  if (!["127.0.0.1:54410", "localhost:54410", "[::1]:54410"].includes(host))
    return false;
  if (
    request.method === "POST" &&
    request.headers.get("origin") !== `http://${host}`
  )
    return false;
  const site = request.headers.get("sec-fetch-site");
  return !site || site === "same-origin" || site === "none";
}

async function proxy(request: Request) {
  if (!allowed(request))
    return Response.json(
      { error: "로컬 개발 환경에서만 사용할 수 있습니다." },
      { status: 403 },
    );
  try {
    const token = await readFile(
      resolve(process.cwd(), "../../.worktrees/evaluation-dashboard/token"),
      "utf8",
    );
    let path = "/status",
      body: string | undefined;
    if (request.method === "POST") {
      const text = await request.text();
      if (text.length > 4096)
        return Response.json({ error: "요청이 너무 큽니다." }, { status: 413 });
      const { action, ...payload } = JSON.parse(text);
      if (!["run", "baseline"].includes(action))
        return Response.json(
          { error: "알 수 없는 작업입니다." },
          { status: 400 },
        );
      path = action === "run" ? "/jobs" : "/baseline";
      body = JSON.stringify(payload);
    }
    const response = await fetch(`http://127.0.0.1:54411${path}`, {
      method: request.method,
      headers: {
        "X-Evaluation-Token": token,
        "Content-Type": "application/json",
      },
      body,
      cache: "no-store",
      signal: AbortSignal.timeout(3000),
    });
    return Response.json(await response.json(), {
      status: response.status,
      headers: { "Cache-Control": "no-store" },
    });
  } catch {
    return Response.json(
      {
        error:
          "로컬 평가 실행기에 연결되지 않았습니다. 실행기를 시작해 주세요.",
      },
      { status: 503 },
    );
  }
}
export const GET = proxy;
export const POST = proxy;

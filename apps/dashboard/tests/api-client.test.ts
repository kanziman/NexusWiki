import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// api-client.ts는 요청자의 현재 세션 토큰을 매 호출마다 새로 읽는다(D-14 정신,
// _user_db 패턴) — createClient().auth.getSession()을 모킹해 실제 Supabase 네트워크
// 호출 없이 세션 유무/토큰 값만 통제한다.
const getSession = vi.fn();

vi.mock("@/lib/supabase/client", () => ({
  createClient: () => ({
    auth: { getSession },
  }),
}));

import { ApiError, apiFetch } from "@/lib/api-client";

const fakeSession = {
  access_token: "fake-access-token",
};

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("apiFetch", () => {
  const originalFetch = global.fetch;
  const originalApiUrl = process.env.NEXT_PUBLIC_API_URL;

  beforeEach(() => {
    getSession.mockReset();
    process.env.NEXT_PUBLIC_API_URL = "http://api.test";
  });

  afterEach(() => {
    global.fetch = originalFetch;
    process.env.NEXT_PUBLIC_API_URL = originalApiUrl;
  });

  it("세션이 없으면 fetch를 호출하기 전에 던진다", async () => {
    getSession.mockResolvedValue({ data: { session: null } });
    const fetchSpy = vi.fn();
    global.fetch = fetchSpy as unknown as typeof fetch;

    await expect(apiFetch("/workspaces/w1/wiki")).rejects.toThrow(
      "apiFetch called without an active session",
    );
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("성공 응답(2xx)은 감싸지 않고 파싱된 본문을 그대로 반환한다", async () => {
    getSession.mockResolvedValue({ data: { session: fakeSession } });
    const fetchSpy = vi
      .fn()
      .mockResolvedValue(jsonResponse(200, { title: "위키 페이지" }));
    global.fetch = fetchSpy as unknown as typeof fetch;

    const result = await apiFetch<{ title: string }>(
      "/workspaces/w1/wiki/slug",
    );

    expect(result).toEqual({ title: "위키 페이지" });
    const [url, requestInit] = fetchSpy.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("http://api.test/workspaces/w1/wiki/slug");
    expect((requestInit.headers as Record<string, string>).Authorization).toBe(
      "Bearer fake-access-token",
    );
  });

  it("본문 없는 202/204 성공 응답은 undefined를 반환한다", async () => {
    getSession.mockResolvedValue({ data: { session: fakeSession } });
    const fetchSpy = vi
      .fn()
      .mockResolvedValue(new Response(null, { status: 202 }));
    global.fetch = fetchSpy as unknown as typeof fetch;

    const result = await apiFetch("/workspaces/w1/jobs/j1/cancel", {
      method: "POST",
    });

    expect(result).toBeUndefined();
  });

  it("403 forbidden -> ApiError(status=403, detail='forbidden')", async () => {
    getSession.mockResolvedValue({ data: { session: fakeSession } });
    global.fetch = vi
      .fn()
      .mockResolvedValue(
        jsonResponse(403, { detail: "forbidden" }),
      ) as unknown as typeof fetch;

    const error = await apiFetch("/workspaces/w1/wiki").catch(
      (e: unknown) => e,
    );

    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).status).toBe(403);
    expect((error as ApiError).detail).toBe("forbidden");
    expect((error as ApiError).extra).toBeUndefined();
  });

  it("409 already_ingested -> extra={raw_source_id}", async () => {
    getSession.mockResolvedValue({ data: { session: fakeSession } });
    global.fetch = vi.fn().mockResolvedValue(
      jsonResponse(409, {
        detail: "already_ingested",
        raw_source_id: "rs-1",
      }),
    ) as unknown as typeof fetch;

    const error = (await apiFetch("/workspaces/w1/sources/text", {
      method: "POST",
      body: { title: "t", text: "x" },
    }).catch((e: unknown) => e)) as ApiError;

    expect(error).toBeInstanceOf(ApiError);
    expect(error.status).toBe(409);
    expect(error.detail).toBe("already_ingested");
    expect(error.extra).toEqual({ raw_source_id: "rs-1" });
  });

  it("402 budget_exceeded -> status=402, detail='budget_exceeded'", async () => {
    getSession.mockResolvedValue({ data: { session: fakeSession } });
    global.fetch = vi
      .fn()
      .mockResolvedValue(
        jsonResponse(402, { detail: "budget_exceeded" }),
      ) as unknown as typeof fetch;

    const error = (await apiFetch("/workspaces/w1/sources/text", {
      method: "POST",
      body: {},
    }).catch((e: unknown) => e)) as ApiError;

    expect(error.status).toBe(402);
    expect(error.detail).toBe("budget_exceeded");
  });

  it("413 text_too_large -> extra={limit: N}", async () => {
    getSession.mockResolvedValue({ data: { session: fakeSession } });
    global.fetch = vi
      .fn()
      .mockResolvedValue(
        jsonResponse(413, { detail: "text_too_large", limit: 50000 }),
      ) as unknown as typeof fetch;

    const error = (await apiFetch("/workspaces/w1/sources/text", {
      method: "POST",
      body: {},
    }).catch((e: unknown) => e)) as ApiError;

    expect(error.status).toBe(413);
    expect(error.detail).toBe("text_too_large");
    expect(error.extra).toEqual({ limit: 50000 });
  });

  it("422 invalid_source -> extra={reason: 'unsupported_mime'}", async () => {
    getSession.mockResolvedValue({ data: { session: fakeSession } });
    global.fetch = vi.fn().mockResolvedValue(
      jsonResponse(422, {
        detail: "invalid_source",
        reason: "unsupported_mime",
      }),
    ) as unknown as typeof fetch;

    const error = (await apiFetch("/workspaces/w1/sources/file", {
      method: "POST",
      body: new Uint8Array([1, 2, 3]),
      contentType: "application/pdf",
    }).catch((e: unknown) => e)) as ApiError;

    expect(error.status).toBe(422);
    expect(error.detail).toBe("invalid_source");
    expect(error.extra).toEqual({ reason: "unsupported_mime" });
  });

  it("409 not_retryable / not_cancellable도 같은 방식으로 매핑된다", async () => {
    getSession.mockResolvedValue({ data: { session: fakeSession } });
    global.fetch = vi
      .fn()
      .mockResolvedValue(
        jsonResponse(409, { detail: "not_retryable" }),
      ) as unknown as typeof fetch;

    const retryError = (await apiFetch("/workspaces/w1/jobs/j1/retry", {
      method: "POST",
    }).catch((e: unknown) => e)) as ApiError;
    expect(retryError.status).toBe(409);
    expect(retryError.detail).toBe("not_retryable");

    global.fetch = vi
      .fn()
      .mockResolvedValue(
        jsonResponse(409, { detail: "not_cancellable" }),
      ) as unknown as typeof fetch;

    const cancelError = (await apiFetch("/workspaces/w1/jobs/j1/cancel", {
      method: "POST",
    }).catch((e: unknown) => e)) as ApiError;
    expect(cancelError.status).toBe(409);
    expect(cancelError.detail).toBe("not_cancellable");
  });

  it("Uint8Array 본문은 raw로 보내고 caller가 지정한 contentType을 싣는다", async () => {
    getSession.mockResolvedValue({ data: { session: fakeSession } });
    const fetchSpy = vi
      .fn()
      .mockResolvedValue(jsonResponse(202, { job_id: "j1" }));
    global.fetch = fetchSpy as unknown as typeof fetch;

    const bytes = new Uint8Array([1, 2, 3]);
    await apiFetch("/workspaces/w1/sources/file?filename=a.pdf&title=A", {
      method: "POST",
      body: bytes,
      contentType: "application/pdf",
    });

    const [, requestInit] = fetchSpy.mock.calls[0] as [string, RequestInit];
    expect(requestInit.body).toBe(bytes);
    expect(
      (requestInit.headers as Record<string, string>)["Content-Type"],
    ).toBe("application/pdf");
  });

  it("일반 객체 본문은 JSON.stringify되고 Content-Type이 application/json이 된다", async () => {
    getSession.mockResolvedValue({ data: { session: fakeSession } });
    const fetchSpy = vi
      .fn()
      .mockResolvedValue(jsonResponse(202, { job_id: "j1" }));
    global.fetch = fetchSpy as unknown as typeof fetch;

    await apiFetch("/workspaces/w1/sources/text", {
      method: "POST",
      body: { title: "t", text: "x" },
    });

    const [, requestInit] = fetchSpy.mock.calls[0] as [string, RequestInit];
    expect(requestInit.body).toBe(JSON.stringify({ title: "t", text: "x" }));
    expect(
      (requestInit.headers as Record<string, string>)["Content-Type"],
    ).toBe("application/json");
  });
});

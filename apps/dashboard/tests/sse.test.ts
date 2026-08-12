import { describe, expect, it } from "vitest";

import { parseSseStream } from "@/lib/sse";

/**
 * 주어진 문자열 청크들을 정확히 그 경계로 흘려보내는 `ReadableStream`을 만든다.
 * 청크 경계를 테스트가 직접 통제해야 "프레임이 청크 경계에서 잘리는" 케이스를
 * 재현할 수 있다.
 */
function streamOf(chunks: string[]): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder();
  return new ReadableStream({
    start(controller) {
      for (const chunk of chunks) {
        controller.enqueue(encoder.encode(chunk));
      }
      controller.close();
    },
  });
}

function responseWithBody(body: ReadableStream<Uint8Array> | null): Response {
  if (body === null) {
    // Response 생성자에 body: null을 넘긴 것과 실제 response.body가 null인 것을
    // 구별하기 위해 명시적으로 null 응답을 만든다.
    return new Response(null, { status: 200 });
  }
  return new Response(body, { status: 200 });
}

async function collect<T>(gen: AsyncGenerator<T>): Promise<T[]> {
  const items: T[] = [];
  for await (const item of gen) {
    items.push(item);
  }
  return items;
}

describe("parseSseStream", () => {
  it("한 청크에 완결된 프레임 하나 -> 항목 하나", async () => {
    const response = responseWithBody(
      streamOf(['event: meta\ndata: {"a":1}\n\n']),
    );

    const items = await collect(parseSseStream(response));

    expect(items).toEqual([{ event: "meta", data: { a: 1 } }]);
  });

  it("같은 프레임이 두 청크 경계에서 잘려도 완결된 항목 하나로 재조립된다", async () => {
    const response = responseWithBody(
      streamOf(['event: meta\ndata: {"a"', ":1}\n\n"]),
    );

    const items = await collect(parseSseStream(response));

    expect(items).toEqual([{ event: "meta", data: { a: 1 } }]);
  });

  it("한 청크에 여러 프레임이 있으면 순서대로 여러 항목을 낸다", async () => {
    const response = responseWithBody(
      streamOf(["event: a\ndata: {}\n\nevent: b\ndata: {}\n\n"]),
    );

    const items = await collect(parseSseStream(response));

    expect(items).toEqual([
      { event: "a", data: {} },
      { event: "b", data: {} },
    ]);
  });

  it("response.body가 null이면 항목 없이 조용히 끝난다", async () => {
    const response = responseWithBody(null);
    expect(response.body).toBeNull();

    const items = await collect(parseSseStream(response));

    expect(items).toEqual([]);
  });
});

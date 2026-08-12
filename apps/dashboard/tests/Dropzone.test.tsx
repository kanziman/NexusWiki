import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

// apiFetch만 모킹하고 ApiError는 실제 클래스를 그대로 쓴다 — Dropzone이 그 실제
// 클래스의 instanceof 분기(mapIngestError)로 동작하므로, 모킹된 가짜 클래스를
// 쓰면 분기 자체가 검증되지 않는다.
const apiFetch = vi.fn();

vi.mock("@/lib/api-client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api-client")>();
  return { ...actual, apiFetch: (...args: unknown[]) => apiFetch(...args) };
});

import { Dropzone } from "@/components/Dropzone";
import { ApiError } from "@/lib/api-client";

function makeFile(name = "note.pdf", type = "application/pdf") {
  return new File(["dummy content"], name, { type });
}

describe("Dropzone", () => {
  beforeEach(() => {
    apiFetch.mockReset();
  });

  it("파일 탭 제출은 raw File을 body로 apiFetch를 호출하고 FormData/multipart를 쓰지 않는다", async () => {
    apiFetch.mockResolvedValue({ job_id: "job-1", raw_source_id: "src-1" });
    const onIngested = vi.fn();
    render(<Dropzone workspaceId="ws-1" onIngested={onIngested} />);

    fireEvent.change(screen.getByLabelText("제목"), {
      target: { value: "노트" },
    });
    const file = makeFile();
    fireEvent.change(screen.getByLabelText("파일 선택"), {
      target: { files: [file] },
    });
    fireEvent.click(screen.getByRole("button", { name: "소스 등록" }));

    await waitFor(() =>
      expect(onIngested).toHaveBeenCalledWith("job-1", "src-1"),
    );

    expect(apiFetch).toHaveBeenCalledTimes(1);
    const [path, init] = apiFetch.mock.calls[0] as [
      string,
      { method: string; body: unknown; contentType?: string },
    ];

    const requestUrl = new URL(path, "http://example.test");
    expect(requestUrl.pathname).toBe("/workspaces/ws-1/sources/file");
    expect(requestUrl.searchParams.get("filename")).toBe(file.name);
    expect(requestUrl.searchParams.get("title")).toBe("노트");

    expect(init.method).toBe("POST");
    expect(init.body).toBe(file);
    expect(init.body).toBeInstanceOf(File);
    expect(init.body).not.toBeInstanceOf(FormData);
    expect(init.contentType).toBe(file.type);
  });

  it("URL 탭에서 http(s) 외 스킴은 요청 없이 인라인 에러를 보여준다", async () => {
    const user = userEvent.setup();
    render(<Dropzone workspaceId="ws-1" />);
    // Radix Tabs의 기본 activationMode는 "automatic"이라 실제 브라우저의 포커스
    // 이동을 동반한다 — fireEvent.click은 포커스를 옮기지 않아 탭이 전환되지
    // 않으므로, 포커스까지 시뮬레이션하는 userEvent를 쓴다.
    await user.click(screen.getByRole("tab", { name: "URL" }));

    fireEvent.change(screen.getByLabelText("URL 주소"), {
      target: { value: "ftp://example.com/file" },
    });
    fireEvent.click(screen.getByRole("button", { name: "소스 등록" }));

    await screen.findByText(
      "http:// 또는 https://로 시작하는 URL만 등록할 수 있습니다.",
    );
    expect(apiFetch).not.toHaveBeenCalled();
  });

  it("URL 탭에서 유효한 URL은 apiFetch로 제출된다", async () => {
    apiFetch.mockResolvedValue({ job_id: "job-2", raw_source_id: "src-2" });
    const user = userEvent.setup();
    render(<Dropzone workspaceId="ws-1" />);
    await user.click(screen.getByRole("tab", { name: "URL" }));

    fireEvent.change(screen.getByLabelText("URL 주소"), {
      target: { value: "https://example.com/doc" },
    });
    fireEvent.click(screen.getByRole("button", { name: "소스 등록" }));

    await waitFor(() => expect(apiFetch).toHaveBeenCalledTimes(1));
    expect(apiFetch).toHaveBeenCalledWith("/workspaces/ws-1/sources/url", {
      method: "POST",
      body: { url: "https://example.com/doc", title: undefined },
    });
  });

  it("텍스트 탭에서 본문이 비어있으면 제출이 비활성화된다", async () => {
    const user = userEvent.setup();
    render(<Dropzone workspaceId="ws-1" />);
    await user.click(screen.getByRole("tab", { name: "텍스트" }));

    fireEvent.change(screen.getByLabelText("제목"), {
      target: { value: "메모" },
    });

    expect(screen.getByRole("button", { name: "소스 등록" })).toBeDisabled();
  });

  it("409 already_ingested면 정확한 배너 문구를 렌더링한다", async () => {
    apiFetch.mockRejectedValue(
      new ApiError(409, "already_ingested", { raw_source_id: "src-9" }),
    );
    render(<Dropzone workspaceId="ws-1" />);

    fireEvent.change(screen.getByLabelText("제목"), {
      target: { value: "노트" },
    });
    fireEvent.change(screen.getByLabelText("파일 선택"), {
      target: { files: [makeFile()] },
    });
    fireEvent.click(screen.getByRole("button", { name: "소스 등록" }));

    await screen.findByText("이미 수집됨 — 건너뜀");
  });

  it("402 budget_exceeded면 정확한 배너 문구를 렌더링한다", async () => {
    apiFetch.mockRejectedValue(new ApiError(402, "budget_exceeded"));
    render(<Dropzone workspaceId="ws-1" />);

    fireEvent.change(screen.getByLabelText("제목"), {
      target: { value: "노트" },
    });
    fireEvent.change(screen.getByLabelText("파일 선택"), {
      target: { files: [makeFile()] },
    });
    fireEvent.click(screen.getByRole("button", { name: "소스 등록" }));

    await screen.findByText(
      "이번 달 워크스페이스 사용량 한도를 초과했습니다. 관리자에게 문의하거나 다음 달까지 기다려주세요.",
    );
  });

  it("422 invalid_source(unsupported_mime)면 원본 MIME을 노출하지 않는 일반 안내를 렌더링한다", async () => {
    apiFetch.mockRejectedValue(
      new ApiError(422, "invalid_source", { reason: "unsupported_mime" }),
    );
    render(<Dropzone workspaceId="ws-1" />);

    fireEvent.change(screen.getByLabelText("제목"), {
      target: { value: "노트" },
    });
    fireEvent.change(screen.getByLabelText("파일 선택"), {
      target: { files: [makeFile("weird.exe", "application/x-msdownload")] },
    });
    fireEvent.click(screen.getByRole("button", { name: "소스 등록" }));

    const message = await screen.findByText(
      "지원하지 않는 파일 형식입니다. 다른 파일로 다시 시도해주세요.",
    );
    expect(message.textContent).not.toContain("application/x-msdownload");
  });
});

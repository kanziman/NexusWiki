import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

const notFound = vi.hoisted(() =>
  vi.fn(() => {
    throw new Error("not-found");
  }),
);

vi.mock("next/navigation", () => ({ notFound }));

import PreviewLayout from "@/app/preview/layout";

describe("preview layout", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    notFound.mockClear();
  });

  it("renders preview children only in development", () => {
    vi.stubEnv("NODE_ENV", "development");

    render(PreviewLayout({ children: <p>목업 화면</p> }));

    expect(screen.getByText("목업 화면")).toBeInTheDocument();
    expect(notFound).not.toHaveBeenCalled();
  });

  it("returns the not-found outcome outside development", () => {
    vi.stubEnv("NODE_ENV", "production");

    expect(() => PreviewLayout({ children: <p>목업 화면</p> })).toThrow(
      "not-found",
    );
    expect(notFound).toHaveBeenCalledOnce();
  });
});

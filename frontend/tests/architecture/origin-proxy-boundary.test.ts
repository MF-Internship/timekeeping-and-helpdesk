import { describe, expect, it } from "vitest";

import nextConfig, { API_PROXY_SOURCE, API_PROXY_TRAILING_SOURCE } from "../../next.config";
import { buildOriginHeaders, config } from "@/middleware";

describe("origin proxy boundary", () => {
  it("removes the client value before attaching the server value", () => {
    const headers = buildOriginHeaders(
      new Headers({ "X-Origin-Credential": "client-controlled" }),
      "X-Origin-Credential",
      "server-only-value",
    );

    expect(headers.get("X-Origin-Credential")).toBe("server-only-value");
    expect([...headers.values()]).not.toContain("client-controlled");
  });

  it("uses one literal matcher and rewrite source", () => {
    expect(config.matcher).toEqual([API_PROXY_SOURCE]);
    expect(API_PROXY_SOURCE).toBe("/api/v1/:path*");
  });

  it("preserves trailing slashes when proxying Django routes", async () => {
    const rewrites = await nextConfig.rewrites?.();

    expect(rewrites).toEqual([
      expect.objectContaining({
        source: API_PROXY_TRAILING_SOURCE,
        destination: expect.stringMatching(/\/api\/v1\/:path\*\/$/),
      }),
      expect.objectContaining({
        source: API_PROXY_SOURCE,
        destination: expect.stringMatching(/\/api\/v1\/:path\*$/),
      }),
    ]);
  });

  it("does not expose a public origin secret", () => {
    expect(Object.keys(process.env).some((key) => key.startsWith("NEXT_PUBLIC_ORIGIN"))).toBe(
      false,
    );
  });
});

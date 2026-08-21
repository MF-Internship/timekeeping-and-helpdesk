import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, resolve } from "node:path";
import { describe, expect, it } from "vitest";

import nextConfig, { API_PROXY_SOURCE, API_PROXY_TRAILING_SOURCE } from "../../next.config";
import { buildOriginHeaders, config } from "@/middleware";

/**
 * Every browser-side feature module. The proxy is only a boundary if nothing
 * routes around it, so the set is enumerated rather than sampled, and guidance
 * is a member of it: the preview reads the Location directory through the same
 * same-origin path every other module uses, and adds no origin of its own
 * (FR-030, SC-005).
 */
const CLIENT_MODULES = [
  "src/features/attendance",
  "src/features/guidance",
  "src/features/home",
  "src/features/identity",
  "src/features/locations",
  "src/features/notifications",
  "src/features/operations",
  "src/features/reports",
  "src/features/tasks",
];

function sourceFiles(directory: string): string[] {
  return readdirSync(directory).flatMap((entry) => {
    const path = join(directory, entry);
    if (statSync(path).isDirectory()) return sourceFiles(path);
    return /\.tsx?$/.test(path) ? [path] : [];
  });
}

function moduleSources(module: string): Array<[string, string]> {
  return sourceFiles(resolve(module)).map((path) => [path, readFileSync(path, "utf8")]);
}

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

describe("no client module introduces an origin of its own", () => {
  it("enumerates the guidance module among the guarded ones", () => {
    expect(CLIENT_MODULES).toContain("src/features/guidance");
    expect(readdirSync(resolve("src/features")).sort()).toEqual(
      CLIENT_MODULES.map((module) => module.replace("src/features/", "")).sort(),
    );
  });

  it.each(CLIENT_MODULES)("%s names no absolute origin", (module) => {
    const sources = moduleSources(module);

    expect(sources.length).toBeGreaterThan(0);
    expect(sources.filter(([, code]) => /https?:\/\//.test(code)).map(([path]) => path)).toEqual(
      [],
    );
  });

  it.each(CLIENT_MODULES)("%s reads no origin out of the environment", (module) => {
    const offenders = moduleSources(module)
      .filter(([, code]) => /process\s*\.\s*env|NEXT_PUBLIC_/.test(code))
      .filter(
        ([path, code]) =>
          !path.endsWith("web-push-config.ts") ||
          /NEXT_PUBLIC_(?!WEB_PUSH_APPLICATION_SERVER_KEY)/.test(code),
      )
      .map(([path]) => path);

    expect(offenders).toEqual([]);
  });

  it("keeps the shared API client on a relative base URL", () => {
    const client = readFileSync(resolve("src/shared/api/client.ts"), "utf8");

    expect(client).toMatch(/baseUrl:\s*""/);
  });
});

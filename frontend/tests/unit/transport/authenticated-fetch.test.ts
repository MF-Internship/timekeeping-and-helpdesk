import { afterEach, describe, expect, it, vi } from "vitest";

import { authenticatedFetch } from "@/shared/transport/authenticated-fetch";

afterEach(() => vi.unstubAllGlobals());

describe("authenticatedFetch", () => {
  it("calls the platform transport once with safe defaults", async () => {
    const platformFetch = vi.fn().mockResolvedValue(new Response(null, { status: 204 }));
    vi.stubGlobal("fetch", platformFetch);
    const controller = new AbortController();

    await authenticatedFetch("/api/v1/schema/", {
      method: "POST",
      body: "{}",
      signal: controller.signal,
      headers: { "Content-Type": "application/json" },
    });

    expect(platformFetch).toHaveBeenCalledTimes(1);
    const [target, init] = platformFetch.mock.calls[0] as [string, RequestInit];
    expect(target).toBe("/api/v1/schema/");
    expect(init.credentials).toBe("include");
    expect(init.cache).toBe("no-store");
    expect(init.signal).toBe(controller.signal);
    expect(new Headers(init.headers).get("Accept")).toBe("application/json");
  });

  it.each(["https://example.invalid/api/v1/schema/", "/outside/"])(
    "rejects %s before network activity",
    async (target) => {
      const platformFetch = vi.fn();
      vi.stubGlobal("fetch", platformFetch);

      await expect(authenticatedFetch(target)).rejects.toThrow("API target");
      expect(platformFetch).not.toHaveBeenCalled();
    },
  );
});

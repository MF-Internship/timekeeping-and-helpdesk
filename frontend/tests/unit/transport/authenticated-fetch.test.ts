import { afterEach, describe, expect, it, vi } from "vitest";

import {
  authenticatedFetch,
  clearMemoryAccessToken,
  setAuthenticationFailureHandler,
  setMemoryAccessToken,
} from "@/shared/transport/authenticated-fetch";

afterEach(() => {
  clearMemoryAccessToken();
  setAuthenticationFailureHandler(undefined);
  vi.unstubAllGlobals();
});

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

  it("shares one refresh and replays ten simultaneous invalid-token requests once", async () => {
    setMemoryAccessToken("old-access");
    let refreshCalls = 0;
    const platformFetch = vi.fn(async (target: string | URL | Request, init?: RequestInit) => {
      if (target === "/api/v1/auth/refresh") {
        refreshCalls += 1;
        await Promise.resolve();
        return new Response(JSON.stringify({ access: "new-access" }), { status: 200 });
      }
      const authorization = new Headers(init?.headers).get("Authorization");
      return authorization === "Bearer new-access"
        ? new Response(null, { status: 204 })
        : new Response(JSON.stringify({ error_code: "INVALID_TOKEN" }), { status: 401 });
    });
    vi.stubGlobal("fetch", platformFetch);

    const responses = await Promise.all(
      Array.from({ length: 10 }, (_, index) =>
        authenticatedFetch(`/api/v1/users/?page=${index + 1}`),
      ),
    );

    expect(refreshCalls).toBe(1);
    expect(responses.every((response) => response.status === 204)).toBe(true);
    expect(platformFetch).toHaveBeenCalledTimes(21);
  });

  it.each(["PERMISSION_DENIED", "VALIDATION_FAILED"])(
    "does not refresh or replay a %s response",
    async (errorCode) => {
      const platformFetch = vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ error_code: errorCode }), {
          status: errorCode === "PERMISSION_DENIED" ? 403 : 400,
        }),
      );
      vi.stubGlobal("fetch", platformFetch);
      const response = await authenticatedFetch("/api/v1/users/");
      expect(response.status).toBe(errorCode === "PERMISSION_DENIED" ? 403 : 400);
      expect(platformFetch).toHaveBeenCalledTimes(1);
    },
  );

  it("clears access and reports inactive without refresh or replay", async () => {
    setMemoryAccessToken("stale-access");
    const failure = vi.fn();
    setAuthenticationFailureHandler(failure);
    const platformFetch = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ error_code: "ACCOUNT_INACTIVE" }), { status: 401 }),
      )
      .mockResolvedValueOnce(new Response(null, { status: 204 }));
    vi.stubGlobal("fetch", platformFetch);
    await authenticatedFetch("/api/v1/me/");
    await authenticatedFetch("/api/v1/schema/");
    expect(failure).toHaveBeenCalledWith("ACCOUNT_INACTIVE");
    expect(new Headers(platformFetch.mock.calls[1][1].headers).has("Authorization")).toBe(false);
    expect(platformFetch).toHaveBeenCalledTimes(2);
  });

  it("reports forced password change without attempting refresh", async () => {
    const failure = vi.fn();
    setAuthenticationFailureHandler(failure);
    const platformFetch = vi
      .fn()
      .mockResolvedValue(
        new Response(JSON.stringify({ error_code: "PASSWORD_CHANGE_REQUIRED" }), { status: 403 }),
      );
    vi.stubGlobal("fetch", platformFetch);
    await authenticatedFetch("/api/v1/users/");
    expect(failure).toHaveBeenCalledWith("PASSWORD_CHANGE_REQUIRED");
    expect(platformFetch).toHaveBeenCalledTimes(1);
  });

  it("reports one anonymous transition when ten requests share a failed refresh", async () => {
    setMemoryAccessToken("expired-access");
    const failure = vi.fn();
    setAuthenticationFailureHandler(failure);
    const platformFetch = vi.fn(async (...args: [string | URL | Request, RequestInit?]) =>
      args[0] === "/api/v1/auth/refresh"
        ? new Response(JSON.stringify({ error_code: "INVALID_TOKEN" }), { status: 401 })
        : new Response(JSON.stringify({ error_code: "INVALID_TOKEN" }), { status: 401 }),
    );
    vi.stubGlobal("fetch", platformFetch);

    await Promise.all(Array.from({ length: 10 }, () => authenticatedFetch("/api/v1/me/")));
    await authenticatedFetch("/api/v1/schema/");

    expect(failure).toHaveBeenCalledTimes(1);
    expect(failure).toHaveBeenCalledWith("INVALID_TOKEN");
    const finalHeaders = new Headers(platformFetch.mock.calls.at(-1)?.[1]?.headers);
    expect(finalHeaders.has("Authorization")).toBe(false);
  });

  it("does not let an old account refresh overwrite a newer login token", async () => {
    setMemoryAccessToken("account-a");
    let releaseRefresh: (() => void) | undefined;
    const refreshReleased = new Promise<void>((resolve) => {
      releaseRefresh = resolve;
    });
    const platformFetch = vi.fn(async (target: string | URL | Request, init?: RequestInit) => {
      if (target === "/api/v1/auth/refresh") {
        await refreshReleased;
        return new Response(JSON.stringify({ access: "stale-account-a" }), { status: 200 });
      }
      const token = new Headers(init?.headers).get("Authorization");
      return token === "Bearer account-b"
        ? new Response(null, { status: 204 })
        : new Response(JSON.stringify({ error_code: "INVALID_TOKEN" }), { status: 401 });
    });
    vi.stubGlobal("fetch", platformFetch);

    const request = authenticatedFetch("/api/v1/me/");
    await vi.waitFor(() => expect(platformFetch).toHaveBeenCalledTimes(2));
    setMemoryAccessToken("account-b");
    releaseRefresh?.();

    expect((await request).status).toBe(204);
    const replayHeaders = new Headers(platformFetch.mock.calls.at(-1)?.[1]?.headers);
    expect(replayHeaders.get("Authorization")).toBe("Bearer account-b");
  });
});

import { describe, expect, it, vi } from "vitest";

const createClient = vi.fn(() => ({ foundation: true }));
vi.mock("openapi-fetch", () => ({ default: createClient }));
vi.mock("@/shared/transport/authenticated-fetch", () => ({
  authenticatedFetch: vi.fn(),
}));

describe("typed API client", () => {
  it("assembles openapi-fetch through authenticatedFetch", async () => {
    const { authenticatedFetch } = await import("@/shared/transport/authenticated-fetch");
    const { apiClient } = await import("@/shared/api/client");
    expect(apiClient).toBeDefined();
    expect(createClient).toHaveBeenCalledWith({ baseUrl: "", fetch: authenticatedFetch });
  });
});

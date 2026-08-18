import { describe, expect, it, vi } from "vitest";

const client = vi.hoisted(() => ({ POST: vi.fn(), GET: vi.fn(), PATCH: vi.fn() }));
vi.mock("@/shared/api/client", () => ({ apiClient: client }));

import { login } from "@/features/identity/api/identity-api";

describe("identity typed API failure contract", () => {
  it("parses canonical failures before exposing them to forms", async () => {
    const requestId = "123e4567-e89b-42d3-a456-426614174000";
    client.POST.mockResolvedValue({
      error: { ignored: true },
      response: new Response(
        JSON.stringify({
          error: "INVALID_CREDENTIALS",
          error_code: "INVALID_CREDENTIALS",
          message: "Thông tin đăng nhập không hợp lệ.",
          details: {},
          request_id: requestId,
        }),
        { status: 401, headers: { "X-Request-Id": requestId } },
      ),
    });

    await expect(login({ username: "worker", password: "wrong" })).rejects.toEqual({
      kind: "canonical",
      errorCode: "INVALID_CREDENTIALS",
      message: "Thông tin đăng nhập không hợp lệ.",
      details: {},
      requestId,
    });
  });
});

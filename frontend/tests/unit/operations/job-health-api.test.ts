import { describe, expect, it, vi } from "vitest";

const client = vi.hoisted(() => ({ GET: vi.fn() }));
vi.mock("@/shared/api/client", () => ({ apiClient: client }));

import { getJobHealth } from "@/features/operations/api/job-health-api";

describe("job health typed GET API", () => {
  it("uses only the canonical GET transport", async () => {
    client.GET.mockResolvedValue({ data: { state: "unknown" }, response: new Response() });
    await expect(getJobHealth()).resolves.toMatchObject({ state: "unknown" });
    expect(client.GET).toHaveBeenCalledWith("/api/v1/operations/job-health");
  });

  it("maps canonical and unexpected failures", async () => {
    const requestId = "123e4567-e89b-42d3-a456-426614174000";
    client.GET.mockResolvedValueOnce({
      error: {
        error: "PERMISSION_DENIED",
        error_code: "PERMISSION_DENIED",
        message: "Không có quyền.",
        details: {},
        request_id: requestId,
      },
      response: new Response(null, {
        status: 403,
        headers: { "X-Request-Id": requestId },
      }),
    });
    await expect(getJobHealth()).rejects.toMatchObject({
      kind: "canonical",
      errorCode: "PERMISSION_DENIED",
    });
    client.GET.mockResolvedValueOnce({
      error: { invalid: true },
      response: new Response(null, { status: 502 }),
    });
    await expect(getJobHealth()).rejects.toMatchObject({
      kind: "unexpected_response",
      status: 502,
    });
  });
});

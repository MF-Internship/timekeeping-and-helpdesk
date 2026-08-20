import { describe, expect, it, vi } from "vitest";

const client = vi.hoisted(() => ({ PATCH: vi.fn() }));
vi.mock("@/shared/api/client", () => ({ apiClient: client }));

import { updateLocation } from "@/features/locations/api/location-api";

describe("Location typed API failure contract", () => {
  it("parses a consumed openapi-fetch conflict body", async () => {
    const requestId = "123e4567-e89b-42d3-a456-426614174000";
    client.PATCH.mockResolvedValue({
      error: {
        error: "LOCATION_VERSION_CONFLICT",
        error_code: "LOCATION_VERSION_CONFLICT",
        message: "Dữ liệu địa điểm đã được thay đổi.",
        details: { version: ["4"], reason: ["Acceptance T107"] },
        version: ["4"],
        reason: ["Acceptance T107"],
        request_id: requestId,
      },
      response: new Response(null, { status: 409, headers: { "X-Request-Id": requestId } }),
    });

    await expect(
      updateLocation(51, { version: 3, name: "Bản nháp", reason: "Acceptance T107" }),
    ).rejects.toMatchObject({ kind: "canonical", errorCode: "LOCATION_VERSION_CONFLICT" });
  });
});

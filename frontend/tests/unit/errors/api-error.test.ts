import { describe, expect, it } from "vitest";

import { networkFailure, parseApiFailure } from "@/shared/errors/api-error";

const requestId = "00000000-0000-4000-8000-000000000000";

describe("API failure parsing", () => {
  it("preserves a canonical v1 envelope", async () => {
    const failure = await parseApiFailure(
      new Response(
        JSON.stringify({
          error_code: "VALIDATION_FAILED",
          error: "VALIDATION_FAILED",
          message: "Dữ liệu không hợp lệ.",
          details: { field_name: ["Giá trị không hợp lệ."] },
          field_name: ["Giá trị không hợp lệ."],
          request_id: requestId,
        }),
        { status: 400, headers: { "X-Request-Id": requestId } },
      ),
    );

    expect(failure.kind).toBe("canonical");
    if (failure.kind !== "canonical") throw new Error("expected canonical failure");
    expect(failure.requestId).toBe(requestId);
  });

  it.each(["NOT_FOUND", "LOCATION_VERSION_CONFLICT"])(
    "preserves the Feature 003 canonical code %s",
    async (errorCode) => {
      const failure = await parseApiFailure(
        new Response(
          JSON.stringify({
            error_code: errorCode,
            error: errorCode,
            message: "Yêu cầu không thể xử lý.",
            details: {},
            request_id: requestId,
          }),
          { status: 409, headers: { "X-Request-Id": requestId } },
        ),
      );
      expect(failure).toMatchObject({ kind: "canonical", errorCode });
    },
  );

  it("treats a mirror mismatch as unexpected", async () => {
    const failure = await parseApiFailure(
      new Response(
        JSON.stringify({
          error_code: "VALIDATION_FAILED",
          error: "PERMISSION_DENIED",
          message: "Dữ liệu không hợp lệ.",
          details: {},
          request_id: requestId,
        }),
        { status: 400 },
      ),
    );
    expect(failure.kind).toBe("unexpected_response");
  });

  it("does not expose an invalid response body", async () => {
    const failure = await parseApiFailure(
      new Response("<html>unsafe</html>", {
        status: 502,
        headers: { "X-Request-Id": requestId },
      }),
    );
    expect(failure).toEqual({ kind: "unexpected_response", status: 502, requestId });
    expect(JSON.stringify(failure)).not.toContain("unsafe");
  });

  it("represents network failure without fabricating a request ID", () => {
    expect(networkFailure()).toEqual({ kind: "network" });
  });

  it("preserves canonical throttle wait metadata", async () => {
    const failure = await parseApiFailure(
      new Response(
        JSON.stringify({
          error_code: "THROTTLED",
          error: "THROTTLED",
          message: "Quá nhiều yêu cầu.",
          details: {},
          request_id: requestId,
        }),
        {
          status: 429,
          headers: { "X-Request-Id": requestId, "Retry-After": "37" },
        },
      ),
    );
    expect(failure).toMatchObject({
      kind: "canonical",
      errorCode: "THROTTLED",
      retryAfterSeconds: 37,
      requestId,
    });
  });
});

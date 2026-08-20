import { describe, expect, it } from "vitest";

import { webPushConfiguration } from "@/features/notifications/adapters/web-push-config";

describe("web push public configuration", () => {
  it.each([undefined, "", "not+url-safe", "AQID"])("fails closed for %s", (value) => {
    expect(webPushConfiguration(value).kind).toBe(
      value === undefined || value === "" ? "disabled" : "invalid",
    );
  });

  it("accepts only an uncompressed P-256 public key", () => {
    const bytes = new Uint8Array(65);
    bytes[0] = 4;
    const key = btoa(String.fromCharCode(...bytes))
      .replaceAll("+", "-")
      .replaceAll("/", "_")
      .replaceAll("=", "");
    const result = webPushConfiguration(key);
    expect(result.kind).toBe("enabled");
    if (result.kind === "enabled") expect([...result.applicationServerKey]).toEqual([...bytes]);
  });
});

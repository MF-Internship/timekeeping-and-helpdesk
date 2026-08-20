import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

describe("notification privacy boundary", () => {
  it("keeps the service worker generic and routes only through the opaque resolver", () => {
    const source = readFileSync(resolve("public/notification-sw.js"), "utf8");
    expect(source).toContain("/notifications/open/");
    expect(source).toContain("Bạn có thông báo mới");
    expect(source).not.toMatch(
      /full_name|latitude|longitude|accuracy|photo|address|token|cookie|endpoint|p256dh|auth/i,
    );
    expect(source).not.toContain("/api/v1/tasks/");
    expect(source).not.toContain("/api/v1/attendance/");
  });
});

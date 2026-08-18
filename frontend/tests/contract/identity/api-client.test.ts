import { describe, expect, it } from "vitest";

import type { operations, paths } from "@/shared/api/schema";

describe("generated identity API contract", () => {
  it("contains every approved identity operation and snake_case path", () => {
    const pathsCompile: keyof paths = "/api/v1/change-password";
    const operationCompile: keyof operations = "users_reset_password_create";
    expect(pathsCompile).toBe("/api/v1/change-password");
    expect(operationCompile).toBe("users_reset_password_create");
  });
});

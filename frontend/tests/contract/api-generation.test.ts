import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const root = resolve(import.meta.dirname, "../..");

describe("generated API schema", () => {
  it("is derived from the committed OpenAPI and byte-stable", () => {
    const before = readFileSync(resolve(root, "src/shared/api/schema.ts"));
    execFileSync("node", ["scripts/generate-api.mjs", "--check"], { cwd: root });
    execFileSync("node", ["scripts/generate-api.mjs", "--check"], { cwd: root });
    expect(readFileSync(resolve(root, "src/shared/api/schema.ts"))).toEqual(before);
  });

  it("contains all attendance operations and typed candidate error branches", () => {
    const schema = readFileSync(resolve(root, "src/shared/api/schema.ts"), "utf8");
    for (const value of [
      "attendance_check_in",
      "attendance_check_out",
      "attendance_today_retrieve",
      "LocationChoiceRequiredError",
      "InvalidLocationChoiceError",
    ]) {
      expect(schema).toContain(value);
    }
  });
});

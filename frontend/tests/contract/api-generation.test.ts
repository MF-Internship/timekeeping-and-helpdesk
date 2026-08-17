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
});

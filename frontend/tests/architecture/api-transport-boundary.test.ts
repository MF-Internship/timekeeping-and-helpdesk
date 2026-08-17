import { execFileSync } from "node:child_process";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const script = resolve("scripts/check-api-transport.mjs");
const fixtures = resolve("tests/architecture/fixtures/transport");

describe("API transport source boundary", () => {
  it("accepts the one approved transport", () => {
    expect(() => execFileSync("node", [script, resolve(fixtures, "safe")])).not.toThrow();
  });

  it.each(["direct", "alternate"])("rejects the %s transport fixture", (fixture) => {
    expect(() => execFileSync("node", [script, resolve(fixtures, fixture)])).toThrow();
  });
});

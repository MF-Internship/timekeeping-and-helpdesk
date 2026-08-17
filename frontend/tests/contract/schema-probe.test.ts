import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

describe("schema probe contract", () => {
  it("contains a machine schema operation with snake_case request identity", () => {
    const schema = readFileSync(
      resolve(import.meta.dirname, "../../src/shared/api/schema.ts"),
      "utf8",
    );
    expect(schema).toContain("api_schema_retrieve");
    expect(schema).toContain("request_id");
    expect(schema).not.toContain("requestId:");
  });
});

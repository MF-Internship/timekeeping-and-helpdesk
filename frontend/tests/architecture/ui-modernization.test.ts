import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, resolve } from "node:path";
import { describe, expect, it } from "vitest";

function sourceFiles(root: string): string[] {
  return readdirSync(root).flatMap((entry) => {
    const path = join(root, entry);
    return statSync(path).isDirectory()
      ? sourceFiles(path)
      : /\.(tsx?|css)$/.test(path)
        ? [path]
        : [];
  });
}

describe("Feature 015 production presentation", () => {
  it("contains no user-visible feature-number labels", () => {
    const offenders = sourceFiles(resolve("src"))
      .filter((file) => !file.endsWith("schema.ts"))
      .filter((file) => /\bFEATURE\s+0(?:0[1-9]|1[0-5])\b/i.test(readFileSync(file, "utf8")));
    expect(offenders).toEqual([]);
  });

  it("keeps navigation in one typed registry", () => {
    const legacy = readFileSync(resolve("src/shared/ui/shell/employee-navigation.ts"), "utf8");
    expect(legacy).toMatch(/applicationNavigation/);
    expect(legacy).not.toMatch(/href:\s*["']/);
  });
});

import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, resolve } from "node:path";
import { describe, expect, it } from "vitest";

const TOKENS = resolve("src/shared/ui/theme/tokens.css");
const ROOTS = [
  resolve("src/shared/ui"),
  resolve("src/features/guidance/ui"),
  resolve("src/features/attendance/ui"),
];

function styles(path: string): string[] {
  return readdirSync(path).flatMap((entry) => {
    const file = join(path, entry);
    if (statSync(file).isDirectory()) return styles(file);
    return file.endsWith(".css") && file !== TOKENS ? [file] : [];
  });
}

describe("semantic design tokens", () => {
  it("defines the shared brand and state vocabulary", () => {
    const source = readFileSync(TOKENS, "utf8");
    for (const token of [
      "brand-primary",
      "success",
      "critical",
      "surface",
      "border",
      "focus",
      "touch-target",
    ]) {
      expect(source).toContain(
        `--color-${token}`.replace("--color-touch-target", "--touch-target"),
      );
    }
  });

  it("keeps raw hexadecimal colors out of component styles", () => {
    const offenders = ROOTS.flatMap(styles).filter((file) =>
      /#[0-9a-f]{3,8}\b/i.test(readFileSync(file, "utf8")),
    );
    expect(offenders).toEqual([]);
  });
});

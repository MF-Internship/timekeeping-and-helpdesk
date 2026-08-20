import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const layout = readFileSync(resolve("src/shared/ui/shell/ApplicationFrame.tsx"), "utf8");
const page = readFileSync(resolve("src/app/(employee)/attendance/page.tsx"), "utf8");
const shellCss = readFileSync(resolve("src/shared/ui/shell/AppShell.module.css"), "utf8");
const navigationCss = readFileSync(
  resolve("src/shared/ui/shell/PrimaryNavigation.module.css"),
  "utf8",
);

describe("employee application shell contract", () => {
  it("owns the shell once at the authenticated application boundary", () => {
    expect(layout.match(/<AppShell/g)).toHaveLength(1);
    expect(page).not.toMatch(/<(main|header|nav)\b/);
  });

  it("provides bounded content and mobile safe-area clearance", () => {
    expect(shellCss).toContain("max-width: var(--content-max)");
    expect(shellCss).toContain("env(safe-area-inset-bottom)");
    expect(navigationCss).toContain("env(safe-area-inset-bottom)");
  });

  it("switches from bottom bar to rail at the content breakpoint", () => {
    expect(navigationCss).toContain("@media (min-width: 48rem)");
    expect(navigationCss).toMatch(/\.bottom[\s\S]*display: none/);
    expect(navigationCss).toMatch(/\.rail[\s\S]*display: block/);
  });
});

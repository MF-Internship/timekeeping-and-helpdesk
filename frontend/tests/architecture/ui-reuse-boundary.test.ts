import { existsSync, readFileSync, readdirSync, statSync } from "node:fs";
import { join, relative, resolve } from "node:path";
import { describe, expect, it } from "vitest";

const SRC = resolve("src");
const PRIMITIVES = ["button", "card", "badge", "section-heading", "async-state"].map((name) =>
  resolve("src/shared/ui", name),
);
const FEATURE_ROOTS = [resolve("src/features/guidance"), resolve("src/features/attendance")];

function files(root: string): string[] {
  return readdirSync(root).flatMap((entry) => {
    const path = join(root, entry);
    return statSync(path).isDirectory() ? files(path) : /\.tsx?$/.test(path) ? [path] : [];
  });
}

describe("UI reuse boundary", () => {
  it("keeps shared primitives free of feature imports", () => {
    const offenders = PRIMITIVES.flatMap(files).filter((file) =>
      /@\/features\//.test(readFileSync(file, "utf8")),
    );
    expect(offenders).toEqual([]);
  });

  it("has no parallel legacy panel wrappers or feature-local primitive implementations", () => {
    for (const legacy of ["PositionStatus.tsx", "NearbyList.tsx", "TargetSelector.tsx"]) {
      expect(existsSync(resolve("src/features/guidance/ui", legacy))).toBe(false);
    }
    const offenders = FEATURE_ROOTS.flatMap(files).filter((file) =>
      /<button\b|summary-card|editor-card/.test(readFileSync(file, "utf8")),
    );
    expect(offenders.map((file) => relative(SRC, file))).toEqual([]);
  });

  it("keeps GPS and reusable Location presentation free of Attendance imports", () => {
    for (const name of [
      "GpsAccuracyIndicator.tsx",
      "GpsStatusCard.tsx",
      "LocationSummaryCard.tsx",
      "NearbyLocationItem.tsx",
      "NearbyLocations.tsx",
    ]) {
      expect(readFileSync(resolve("src/features/guidance/ui", name), "utf8")).not.toContain(
        "features/attendance",
      );
    }
  });

  it("contains no map provider, tile, iframe, or remote position integration", () => {
    const source = files(resolve("src/features/guidance"))
      .map((file) => readFileSync(file, "utf8"))
      .join("\n");
    expect(source).not.toMatch(/mapbox|leaflet|google\.maps|openstreetmap|<iframe|https?:\/\//i);
    expect(readFileSync(resolve("src/features/guidance/ui/SpatialPanel.tsx"), "utf8")).toContain(
      "dynamic(",
    );
  });
});

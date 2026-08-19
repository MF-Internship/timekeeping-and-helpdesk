import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative, resolve } from "node:path";
import { describe, expect, it } from "vitest";

const SRC_ROOT = resolve("src");
const GUIDANCE_ROOT = resolve("src/features/guidance");

function sourceFiles(directory: string): string[] {
  return readdirSync(directory).flatMap((entry) => {
    const path = join(directory, entry);
    if (statSync(path).isDirectory()) return sourceFiles(path);
    return /\.tsx?$/.test(path) ? [path] : [];
  });
}

type Edge = { file: string; specifier: string };

function importEdges(files: string[]): Edge[] {
  return files.flatMap((path) => {
    const code = readFileSync(path, "utf8");
    return [...code.matchAll(/from\s+"([^"]+)"/g)].map((match) => ({
      file: relative(SRC_ROOT, path),
      specifier: match[1],
    }));
  });
}

const GUIDANCE_FILES = sourceFiles(GUIDANCE_ROOT);
const OUTGOING = importEdges(GUIDANCE_FILES);
const INCOMING = importEdges(sourceFiles(SRC_ROOT)).filter((edge) =>
  edge.specifier.startsWith("@/features/guidance"),
);

const ALLOWED_ALIAS_PREFIXES = ["@/shared/", "@/features/locations/api/", "@/features/guidance/"];

/**
 * The stored-record map link and every external map host it could be spelled
 * as. `maps_url` is produced server-side by `attendance_maps_url`, the single
 * producer of such a link, and belongs to a recorded punch. Guidance previews a
 * position that has not been recorded, so it has no stored record to link to and
 * reaches no map service of its own (T085b, FR-029, FR-029a).
 */
const EXTERNAL_MAP_MARKERS = [
  "maps_url",
  "google.com/maps",
  "maps.apple.com",
  "openstreetmap.org",
  "mapbox.com",
  "geo:",
];

/**
 * The single specifier another feature may import: the rendered preview region,
 * mounted beside the punch controls. It returns markup and nothing else — no
 * distance, no membership status, no threshold — so no geofence decision can be
 * taken through it. Everything that could carry such a decision lives under
 * `model/`, which the next assertion closes off entirely (T033b, FR-034, FR-039).
 */
const ALLOWED_FEATURE_ENTRY_POINTS = new Set([
  "@/features/guidance/ui/GuidancePanel",
  "@/features/guidance/model/guidance-state",
]);

function isAllowedOutgoing({ specifier }: Edge): boolean {
  if (!specifier.startsWith("@/")) return true;
  return ALLOWED_ALIAS_PREFIXES.some((prefix) => specifier.startsWith(prefix));
}

describe("guidance import boundary", () => {
  it("guards a non-empty module", () => {
    expect(GUIDANCE_FILES.length).toBeGreaterThan(0);
    expect(OUTGOING.length).toBeGreaterThan(0);
  });

  it("imports only from shared, the Location API and itself", () => {
    expect(OUTGOING.filter((edge) => !isAllowedOutgoing(edge))).toEqual([]);
  });

  it("never reuses the Attendance punch acquisition", () => {
    const attendance = OUTGOING.filter((edge) =>
      edge.specifier.startsWith("@/features/attendance"),
    );
    expect(attendance).toEqual([]);
  });

  it("exposes no module another feature imports for a geofence decision", () => {
    const fromFeatures = INCOMING.filter(
      (edge) => edge.file.startsWith("features/") && !edge.file.startsWith("features/guidance/"),
    );
    expect(
      fromFeatures.filter((edge) => !ALLOWED_FEATURE_ENTRY_POINTS.has(edge.specifier)),
    ).toEqual([]);
  });

  it("never lets another feature reach the geofence model at all", () => {
    const reachesDecisionModel = INCOMING.filter(
      (edge) =>
        !edge.file.startsWith("features/guidance/") &&
        edge.specifier.startsWith("@/features/guidance/model/") &&
        edge.specifier !== "@/features/guidance/model/guidance-state",
    );
    expect(reachesDecisionModel).toEqual([]);
  });

  it("is never imported by the Location directory", () => {
    expect(INCOMING.filter((edge) => edge.file.startsWith("features/locations/"))).toEqual([]);
  });

  it("reaches no external map link, neither the stored one nor one of its own", () => {
    const offenders = GUIDANCE_FILES.flatMap((path) => {
      const code = readFileSync(path, "utf8");
      return EXTERNAL_MAP_MARKERS.filter((marker) => code.includes(marker)).map(
        (marker) => `${relative(SRC_ROOT, path)}: ${marker}`,
      );
    });
    expect(offenders).toEqual([]);
  });
});

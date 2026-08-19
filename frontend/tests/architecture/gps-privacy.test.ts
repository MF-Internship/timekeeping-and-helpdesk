import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative, resolve } from "node:path";
import { describe, expect, it } from "vitest";

const GUIDANCE_ROOT = resolve("src/features/guidance");

/**
 * The screen that hosts the preview beside the punch controls. Guidance is only
 * as private as its host: a snapshot the module itself never leaks could still
 * escape through the panel that mounts it, so the panel is guarded by the same
 * rules as the module (FR-032, FR-033, FR-039, SC-004).
 */
const HOST_PANEL = resolve("src/features/attendance/ui/AttendancePanel.tsx");
const ATTENDANCE_EXPERIENCE = resolve("src/features/attendance/model/use-attendance-experience.ts");

function sourceFiles(directory: string): string[] {
  return readdirSync(directory).flatMap((entry) => {
    const path = join(directory, entry);
    if (statSync(path).isDirectory()) return sourceFiles(path);
    return /\.tsx?$/.test(path) ? [path] : [];
  });
}

function readGuidanceSources(): Array<[string, string]> {
  return sourceFiles(GUIDANCE_ROOT).map((path) => [
    relative(GUIDANCE_ROOT, path),
    readFileSync(path, "utf8"),
  ]);
}

const SOURCES = readGuidanceSources();

/** Everything that may hold a guidance reading: the module, and its host. */
const GUARDED: Array<[string, string]> = [
  ...SOURCES,
  ["attendance/ui/AttendancePanel.tsx", readFileSync(HOST_PANEL, "utf8")],
  ["attendance/model/use-attendance-experience.ts", readFileSync(ATTENDANCE_EXPERIENCE, "utf8")],
];

const HOST_CODE = readFileSync(HOST_PANEL, "utf8");
const ATTENDANCE_EXPERIENCE_CODE = readFileSync(ATTENDANCE_EXPERIENCE, "utf8");

function offenders(pattern: RegExp): string[] {
  return GUARDED.filter(([, code]) => pattern.test(code)).map(([name]) => name);
}

function guidanceOffenders(pattern: RegExp): string[] {
  return SOURCES.filter(([, code]) => pattern.test(code)).map(([name]) => name);
}

describe("guidance and its host never persist a coordinate", () => {
  it("guards the whole module and the panel that mounts it", () => {
    expect(SOURCES.length).toBeGreaterThan(0);
    expect(GUARDED.map(([name]) => name)).toContain("attendance/ui/AttendancePanel.tsx");
  });

  it.each([
    ["localStorage", /\blocalStorage\b/],
    ["sessionStorage", /\bsessionStorage\b/],
    ["document.cookie", /document\s*\.\s*cookie/],
    ["indexedDB", /\bindexedDB\b/i],
  ])("never touches %s", (_label, pattern) => {
    expect(offenders(pattern)).toEqual([]);
  });
});

describe("guidance and its host never log or report a coordinate", () => {
  it("never calls console", () => {
    expect(offenders(/\bconsole\s*\./)).toEqual([]);
  });

  it.each([
    ["sendBeacon", /\bsendBeacon\b/],
    ["analytics", /\banalytics\b/i],
    ["telemetry", /\btelemetry\b/i],
    ["metrics sinks", /\b(gtag|datadog|posthog|mixpanel|Sentry)\b/],
    ["event tracking", /\btrackEvent\b/],
  ])("never reaches a %s sink", (_label, pattern) => {
    expect(offenders(pattern)).toEqual([]);
  });
});

describe("guidance and its host never put a coordinate on the wire", () => {
  it.each([
    ["a URL", /new URL\(/],
    ["a query string", /URLSearchParams|searchParams/],
    ["a route parameter", /router\s*\.\s*(push|replace)|location\s*\.\s*(href|assign)/],
    ["an external window", /window\s*\.\s*open|https?:\/\//],
  ])("never builds %s", (_label, pattern) => {
    expect(offenders(pattern)).toEqual([]);
  });

  it("issues no request of its own", () => {
    expect(offenders(/\bfetch\s*\(|XMLHttpRequest|navigator\s*\.\s*sendBeacon/)).toEqual([]);
  });

  it("reads the backend only through the shared Location API module", () => {
    const imports = SOURCES.flatMap(([name, code]) =>
      [...code.matchAll(/from\s+"([^"]+)"/g)].map((match) => [name, match[1]] as const),
    );
    const backendImports = imports.filter(([, specifier]) => specifier.includes("/api/"));
    expect(backendImports.map(([, specifier]) => specifier)).toEqual(
      backendImports.map(() => "@/features/locations/api/location-api"),
    );
  });
});

describe("guidance reads only the Attendance accuracy threshold", () => {
  it.each(["task_gps_good_accuracy_m", "task_gps_low_accuracy_m"])("never reads %s", (field) => {
    expect(guidanceOffenders(new RegExp(field))).toEqual([]);
  });

  it("reads max_attendance_accuracy_m", () => {
    expect(guidanceOffenders(/max_attendance_accuracy_m/).length).toBeGreaterThan(0);
  });
});

/**
 * A notification body, a push payload, and a toast are all places a coordinate
 * could surface outside the screen that read it. None of them is written to
 * anywhere in guidance or in its host (FR-033).
 */
describe("guidance and its host never put a coordinate in a notification", () => {
  it.each([
    ["a Notification", /\bNotification\b|\bshowNotification\b/],
    ["a push subscription", /\bpushManager\b|\bPushSubscription\b|\bwebpush\b/i],
    ["a toast", /\btoast\b/i],
  ])("never builds %s payload", (_label, pattern) => {
    expect(offenders(pattern)).toEqual([]);
  });
});

/**
 * The host mounts the preview and reads nothing back from it. The punch payload
 * is built from a sample acquired at press time, so the preview cannot be the
 * source of a punched coordinate even by accident (FR-039, SC-008).
 */
describe("the host keeps preview and punch acquisition separate", () => {
  it("passes guidance only to guidance presentation and holds no ref", () => {
    expect(HOST_CODE).toMatch(/<GuidanceContent\s+guidance={guidance}/);
    expect(HOST_CODE).not.toMatch(/\bref\s*=/);
  });

  it("imports only the guidance hook and its presentation component", () => {
    const guidanceImports = [...HOST_CODE.matchAll(/from\s+"([^"]+)"/g)]
      .map((match) => match[1])
      .filter((specifier) => specifier.includes("features/guidance"));

    expect(guidanceImports).toEqual([
      "@/features/guidance/model/guidance-state",
      "@/features/guidance/ui/GuidancePanel",
    ]);
  });

  it("builds every punch payload from a sample acquired at press time", () => {
    expect(ATTENDANCE_EXPERIENCE_CODE).toMatch(/freshCommand\(acquire/);
    const punches = [...ATTENDANCE_EXPERIENCE_CODE.matchAll(/\b(checkIn|checkOut)\(([^)]*)\)/g)];

    expect(punches).toHaveLength(2);
    expect(punches.map((match) => match[2])).toEqual(["command", "command"]);
  });
});

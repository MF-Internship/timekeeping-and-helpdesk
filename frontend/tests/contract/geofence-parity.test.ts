import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, it } from "vitest";

import {
  DISTANCE_TOLERANCE_M,
  EARTH_RADIUS_M,
  classifyGeofence,
  haversineDistanceM,
  type GeofenceStatus,
} from "@/features/guidance/model/geofence";

type FixturePoint = { latitude: string; longitude: string };

type FixtureCase = {
  id: string;
  description: string;
  origin: FixturePoint;
  destination: FixturePoint;
  expected_distance_m: number;
  radius_m: string;
  expected_status: GeofenceStatus;
};

type Fixture = {
  earth_radius_m: number;
  tolerance_m: number;
  cases: FixtureCase[];
};

const FIXTURE_PATH = resolve(__dirname, "../../../contracts/fixtures/geofence-distance.json");
const fixture = JSON.parse(readFileSync(FIXTURE_PATH, "utf-8")) as Fixture;

function point(value: FixturePoint) {
  return { latitude: Number(value.latitude), longitude: Number(value.longitude) };
}

describe("geofence parity with the canonical server geometry", () => {
  it("uses the same Earth radius constant as the fixture", () => {
    expect(EARTH_RADIUS_M).toBe(fixture.earth_radius_m);
  });

  it("uses the same comparison tolerance as the fixture", () => {
    expect(DISTANCE_TOLERANCE_M).toBe(fixture.tolerance_m);
  });

  it("covers every required fixture scenario", () => {
    expect(fixture.cases.length).toBeGreaterThanOrEqual(14);
    expect(new Set(fixture.cases.map((entry) => entry.id)).size).toBe(fixture.cases.length);
  });

  it.each(fixture.cases.map((entry) => [entry.id, entry] as const))(
    "matches the fixture distance for %s",
    (_id, entry) => {
      const distance = haversineDistanceM(point(entry.origin), point(entry.destination));
      expect(Math.abs(distance - entry.expected_distance_m)).toBeLessThanOrEqual(
        fixture.tolerance_m,
      );
    },
  );

  it.each(fixture.cases.map((entry) => [entry.id, entry] as const))(
    "computes a symmetric distance for %s",
    (_id, entry) => {
      const origin = point(entry.origin);
      const destination = point(entry.destination);
      expect(haversineDistanceM(origin, destination)).toBe(haversineDistanceM(destination, origin));
    },
  );

  it.each(fixture.cases.map((entry) => [entry.id, entry] as const))(
    "matches the fixture classification for %s",
    (_id, entry) => {
      const distance = haversineDistanceM(point(entry.origin), point(entry.destination));
      expect(classifyGeofence(distance, Number(entry.radius_m))).toBe(entry.expected_status);
    },
  );
});

describe("geofence boundary is inclusive", () => {
  const RADIUS_M = 50;

  it("classifies INSIDE at exactly distance === radius", () => {
    expect(classifyGeofence(RADIUS_M, RADIUS_M)).toBe("INSIDE_GEOFENCE");
  });

  it("classifies OUTSIDE one ULP beyond the radius", () => {
    const oneUlpBeyond = nextAfter(RADIUS_M);
    expect(oneUlpBeyond).toBeGreaterThan(RADIUS_M);
    expect(classifyGeofence(oneUlpBeyond, RADIUS_M)).toBe("OUTSIDE_GEOFENCE");
  });

  it("never adjusts the radius by an accuracy value", () => {
    expect(classifyGeofence(RADIUS_M, RADIUS_M)).toBe("INSIDE_GEOFENCE");
    expect(classifyGeofence(nextAfter(RADIUS_M), RADIUS_M)).toBe("OUTSIDE_GEOFENCE");
  });
});

/** Smallest representable double strictly greater than `value`. */
function nextAfter(value: number): number {
  const buffer = new DataView(new ArrayBuffer(8));
  buffer.setFloat64(0, value);
  buffer.setBigUint64(0, buffer.getBigUint64(0) + 1n);
  return buffer.getFloat64(0);
}

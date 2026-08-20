import { describe, expect, it } from "vitest";

import {
  NEARBY_LIMIT,
  projectGuidanceLocation,
  rankNearby,
} from "@/features/guidance/model/nearby";
import type { GuidancePosition } from "@/features/guidance/model/position-types";

const METRES_PER_DEGREE_LATITUDE = 111194.93;

const POSITION: GuidancePosition = {
  latitude: 10,
  longitude: 106,
  accuracyM: 8,
  capturedAt: "2026-08-19T03:00:00.000Z",
};

type Row = Parameters<typeof rankNearby>[1][number];

/** A Location roughly `northM` metres due north of {@link POSITION}. */
function locationAt(code: string, northM: number, overrides: Partial<Row> = {}): Row {
  return {
    code,
    name: `Điểm ${code}`,
    address: `Địa chỉ ${code}`,
    latitude: (POSITION.latitude + northM / METRES_PER_DEGREE_LATITUDE).toFixed(15),
    longitude: POSITION.longitude.toFixed(15),
    radius_m: "50.000",
    is_active: true,
    ...overrides,
  };
}

describe("rankNearby", () => {
  it("returns an empty list when the active directory is empty", () => {
    expect(rankNearby(POSITION, [])).toEqual([]);
  });

  it("excludes inactive Locations", () => {
    const ranked = rankNearby(POSITION, [
      locationAt("A", 10, { is_active: false }),
      locationAt("B", 900),
    ]);

    expect(ranked.map((entry) => entry.code)).toEqual(["B"]);
  });

  it("returns an empty list when every Location is inactive", () => {
    const ranked = rankNearby(POSITION, [
      locationAt("A", 10, { is_active: false }),
      locationAt("B", 20, { is_active: false }),
    ]);

    expect(ranked).toEqual([]);
  });

  it("orders entries by ascending distance", () => {
    const ranked = rankNearby(POSITION, [
      locationAt("C", 900),
      locationAt("A", 100),
      locationAt("B", 400),
    ]);

    expect(ranked.map((entry) => entry.code)).toEqual(["A", "B", "C"]);
    expect(ranked[0].distanceM).toBeLessThan(ranked[1].distanceM);
    expect(ranked[1].distanceM).toBeLessThan(ranked[2].distanceM);
  });

  it("breaks ties at the same distance by the lexicographically smallest code", () => {
    const ranked = rankNearby(POSITION, [
      locationAt("HCM000079", 900),
      locationAt("HCM010005", 900),
      locationAt("HCM000012", 900),
    ]);

    expect(ranked.map((entry) => entry.code)).toEqual(["HCM000012", "HCM000079", "HCM010005"]);
  });

  it("classifies containment and derives both margins from the same distance", () => {
    const [inside, outside] = rankNearby(POSITION, [locationAt("IN", 30), locationAt("OUT", 130)]);

    expect(inside.status).toBe("INSIDE_GEOFENCE");
    expect(inside.distanceToBoundaryM).toBe(0);
    expect(inside.insideMarginM).toBeCloseTo(50 - inside.distanceM, 9);

    expect(outside.status).toBe("OUTSIDE_GEOFENCE");
    expect(outside.insideMarginM).toBe(0);
    expect(outside.distanceToBoundaryM).toBeCloseTo(outside.distanceM - 50, 9);
  });

  it("never promotes a containing Location ahead of a closer non-containing one", () => {
    const ranked = rankNearby(POSITION, [
      locationAt("NEAR-OUT", 60, { radius_m: "20.000" }),
      locationAt("FAR-IN", 200, { radius_m: "400.000" }),
    ]);

    expect(ranked.map((entry) => entry.code)).toEqual(["NEAR-OUT", "FAR-IN"]);
    expect(ranked[0].status).toBe("OUTSIDE_GEOFENCE");
    expect(ranked[1].status).toBe("INSIDE_GEOFENCE");
  });

  it("caps the list at five entries when no geofence contains the position", () => {
    const rows = [100, 200, 300, 400, 500, 600, 700].map((metres, index) =>
      locationAt(`L${index}`, metres),
    );

    const ranked = rankNearby(POSITION, rows);

    expect(ranked).toHaveLength(NEARBY_LIMIT);
    expect(ranked.map((entry) => entry.code)).toEqual(["L0", "L1", "L2", "L3", "L4"]);
  });

  it("keeps every containing Location even when they exceed the cap", () => {
    const rows = [10, 20, 30, 40, 45, 48, 49].map((metres, index) =>
      locationAt(`C${index}`, metres),
    );

    const ranked = rankNearby(POSITION, rows);

    expect(ranked).toHaveLength(7);
    expect(ranked.every((entry) => entry.status === "INSIDE_GEOFENCE")).toBe(true);
  });

  it("fills the remaining slots with the nearest non-containing Locations", () => {
    const rows = [
      locationAt("IN-A", 10),
      locationAt("IN-B", 20),
      ...[100, 200, 300, 400].map((metres, index) => locationAt(`OUT-${index}`, metres)),
    ];

    const ranked = rankNearby(POSITION, rows);

    expect(ranked.map((entry) => entry.code)).toEqual(["IN-A", "IN-B", "OUT-0", "OUT-1", "OUT-2"]);
  });

  it("applies no maximum search distance", () => {
    const ranked = rankNearby(POSITION, [locationAt("FAR", 250_000)]);

    expect(ranked).toHaveLength(1);
    expect(ranked[0].status).toBe("OUTSIDE_GEOFENCE");
    expect(ranked[0].distanceM).toBeGreaterThan(200_000);
  });
});

describe("data minimisation (FR-038)", () => {
  /** Exactly the attributes guidance is allowed to read from a directory row. */
  const PROJECTED_FIELDS = [
    "code",
    "name",
    "address",
    "latitude",
    "longitude",
    "radius_m",
    "is_active",
  ];

  /** A directory row as the API actually returns it, extras and all. */
  const FULL_ROW = {
    ...locationAt("HCM000012", 10),
    id: 12,
    kind: "SHOP",
    parent: 3,
    timezone: "Asia/Ho_Chi_Minh",
    created_at: "2026-01-02T00:00:00Z",
    updated_at: "2026-03-04T00:00:00Z",
  };

  const EXTRA_VALUES = ["kind", "parent", "timezone", "created_at", "updated_at", "SHOP"];

  it("projects a directory row down to exactly the FR-038 attributes", () => {
    const projected = projectGuidanceLocation(FULL_ROW);

    expect(Object.keys(projected).sort()).toEqual([...PROJECTED_FIELDS].sort());
  });

  it("carries no extra directory attribute into guidance state", () => {
    const serialised = JSON.stringify(rankNearby(POSITION, [FULL_ROW]));

    for (const extra of EXTRA_VALUES) {
      expect(serialised).not.toContain(extra);
    }
  });

  it("keeps the surrogate row id out of the ranked entry", () => {
    const [entry] = rankNearby(POSITION, [FULL_ROW]);

    expect(entry).not.toHaveProperty("id");
    expect(entry).not.toHaveProperty("locationId");
    expect(entry.code).toBe("HCM000012");
  });
});

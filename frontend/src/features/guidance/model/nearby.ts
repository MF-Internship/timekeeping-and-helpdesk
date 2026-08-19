import {
  DISTANCE_TOLERANCE_M,
  classifyGeofence,
  haversineDistanceM,
  type GeofenceCoordinates,
} from "./geofence";
import type { GuidancePosition, NearbyEntry } from "./position-types";

/**
 * The list never truncates below this many rows, and never truncates away a
 * Location whose geofence contains the position (FR-013, FR-013a).
 */
export const NEARBY_LIMIT = 5;

/**
 * The narrow projection guidance reads from the Location directory. Nothing
 * outside these fields is carried into the preview (FR-031).
 */
export type GuidanceLocation = {
  code: string;
  name: string;
  address: string;
  latitude: string;
  longitude: string;
  radius_m: string;
  is_active: boolean;
};

export type DirectoryRow = {
  readonly code: string;
  readonly name: string;
  readonly address: string;
  readonly latitude: string;
  readonly longitude: string;
  readonly radius_m: string;
  readonly is_active: boolean;
};

/** Narrows a directory row to exactly the fields guidance is allowed to read. */
export function projectGuidanceLocation(row: DirectoryRow): GuidanceLocation {
  return {
    code: row.code,
    name: row.name,
    address: row.address,
    latitude: row.latitude,
    longitude: row.longitude,
    radius_m: row.radius_m,
    is_active: row.is_active,
  };
}

function coordinatesOf(location: GuidanceLocation): GeofenceCoordinates {
  return { latitude: Number(location.latitude), longitude: Number(location.longitude) };
}

function describe(position: GuidancePosition, location: GuidanceLocation): NearbyEntry {
  const coordinates = coordinatesOf(location);
  const distanceM = haversineDistanceM(position, coordinates);
  const radiusM = Number(location.radius_m);
  return {
    code: location.code,
    name: location.name,
    address: location.address,
    distanceM,
    radiusM,
    status: classifyGeofence(distanceM, radiusM),
    distanceToBoundaryM: Math.max(distanceM - radiusM, 0),
    insideMarginM: Math.max(radiusM - distanceM, 0),
    coordinates,
  };
}

/**
 * Ascending distance. Two distances within the fixture tolerance are a tie and
 * are resolved by the lexicographically smallest `code`, so the order is stable
 * and reproducible. Containment never promotes an entry ahead of a closer
 * non-containing entry (FR-012).
 */
function byDistanceThenCode(left: NearbyEntry, right: NearbyEntry): number {
  const gap = left.distanceM - right.distanceM;
  if (Math.abs(gap) > DISTANCE_TOLERANCE_M) return gap;
  return left.code.localeCompare(right.code);
}

function isUsable(location: GuidanceLocation): boolean {
  return (
    Number.isFinite(Number(location.latitude)) &&
    Number.isFinite(Number(location.longitude)) &&
    Number(location.radius_m) > 0
  );
}

/**
 * The position-independent view of the directory: the same narrow projection,
 * ordered by `code`, carrying no distance and no membership status. It stays
 * readable when no position could be acquired at all (FR-007).
 */
export function listGuidanceLocations(locations: readonly DirectoryRow[]): GuidanceLocation[] {
  return locations
    .map(projectGuidanceLocation)
    .filter((location) => location.is_active && isUsable(location))
    .sort((left, right) => left.code.localeCompare(right.code));
}

/**
 * Ranks the active Location directory against an on-device position.
 *
 * No maximum search distance is applied: when the directory holds only distant
 * Locations the nearest ones are still listed (FR-013a).
 */
export function rankNearby(
  position: GuidancePosition,
  locations: readonly DirectoryRow[],
): NearbyEntry[] {
  const ranked = locations
    .map(projectGuidanceLocation)
    .filter((location) => location.is_active && isUsable(location))
    .map((location) => describe(position, location))
    .sort(byDistanceThenCode);

  const containing = ranked.filter((entry) => entry.status === "INSIDE_GEOFENCE");
  const outside = ranked.filter((entry) => entry.status === "OUTSIDE_GEOFENCE");
  const fill = Math.max(NEARBY_LIMIT - containing.length, 0);
  return [...containing, ...outside.slice(0, fill)].sort(byDistanceThenCode);
}

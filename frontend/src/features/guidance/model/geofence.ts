/**
 * Client mirror of the canonical server geometry in
 * `backend/locations/domain/geofence.py`.
 *
 * This file MUST stay arithmetically identical to that module. It is pinned to
 * it by `contracts/fixtures/geofence-distance.json`, asserted from both
 * languages (FR-043a). No second distance formula, no second Earth radius, and
 * no third classification state may be introduced anywhere.
 */

export const EARTH_RADIUS_M = 6371008.8;

export type GeofenceStatus = "INSIDE_GEOFENCE" | "OUTSIDE_GEOFENCE";

/**
 * Two distances closer together than this are indistinguishable. Pinned to
 * `tolerance_m` in `contracts/fixtures/geofence-distance.json` and asserted by
 * `frontend/tests/contract/geofence-parity.test.ts`.
 */
export const DISTANCE_TOLERANCE_M = 0.001;

export type GeofenceCoordinates = {
  latitude: number;
  longitude: number;
};

const DEGREES_PER_HALF_TURN = 180;

function toRadians(degrees: number): number {
  return (degrees * Math.PI) / DEGREES_PER_HALF_TURN;
}

export function haversineDistanceM(
  origin: GeofenceCoordinates,
  destination: GeofenceCoordinates,
): number {
  const lat1 = toRadians(origin.latitude);
  const lon1 = toRadians(origin.longitude);
  const lat2 = toRadians(destination.latitude);
  const lon2 = toRadians(destination.longitude);
  const deltaLat = lat2 - lat1;
  const deltaLon = lon2 - lon1;
  const value =
    Math.sin(deltaLat / 2) ** 2 + Math.cos(lat1) * Math.cos(lat2) * Math.sin(deltaLon / 2) ** 2;
  return EARTH_RADIUS_M * 2 * Math.asin(Math.min(1, Math.sqrt(value)));
}

export function classifyGeofence(distanceM: number, radiusM: number): GeofenceStatus {
  if (!Number.isFinite(distanceM) || distanceM < 0) {
    throw new Error("distance_m");
  }
  if (!Number.isFinite(radiusM) || radiusM <= 0) {
    throw new Error("radius_m");
  }
  return distanceM <= radiusM ? "INSIDE_GEOFENCE" : "OUTSIDE_GEOFENCE";
}

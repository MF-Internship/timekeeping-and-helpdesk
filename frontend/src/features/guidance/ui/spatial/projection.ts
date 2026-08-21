import { EARTH_RADIUS_M, type GeofenceCoordinates } from "../../model/geofence";
import type { GuidancePosition, NearbyEntry } from "../../model/position-types";

export const VIEWPORT = 320;
export const PADDING = 28;
const HALVES_PER_WHOLE = 2;
export const CENTRE = VIEWPORT / HALVES_PER_WHOLE;
const DRAWABLE_HALF = CENTRE - PADDING;
const DEGREES_PER_HALF_TURN = 180;
const METRES_PER_DEGREE = (Math.PI * EARTH_RADIUS_M) / DEGREES_PER_HALF_TURN;
const MIN_EXTENT_M = 5;

export type Offset = { eastM: number; northM: number };
export type Point = { x: number; y: number };
export type Geometry = { scale: number; target: Point; accuracyR: number };

export function offsetOf(origin: GeofenceCoordinates, point: GeofenceCoordinates): Offset {
  const latitudeScale = Math.cos((origin.latitude * Math.PI) / DEGREES_PER_HALF_TURN);
  return {
    eastM: (point.longitude - origin.longitude) * METRES_PER_DEGREE * latitudeScale,
    northM: (point.latitude - origin.latitude) * METRES_PER_DEGREE,
  };
}

export function place(offset: Offset, scale: number): Point {
  return { x: CENTRE + offset.eastM * scale, y: CENTRE - offset.northM * scale };
}

export function isOnCanvas(point: Point): boolean {
  return point.x >= 0 && point.x <= VIEWPORT && point.y >= 0 && point.y <= VIEWPORT;
}

function usable(position: GuidancePosition, focused: NearbyEntry): boolean {
  return (
    [
      position.latitude,
      position.longitude,
      position.accuracyM,
      focused.coordinates.latitude,
      focused.coordinates.longitude,
      focused.radiusM,
    ].every(Number.isFinite) &&
    position.accuracyM >= 0 &&
    focused.radiusM >= 0
  );
}

export function fit(position?: GuidancePosition, focused?: NearbyEntry): Geometry | undefined {
  if (!position || !focused || !usable(position, focused)) return undefined;
  const offset = offsetOf(position, focused.coordinates);
  if (![offset.eastM, offset.northM].every(Number.isFinite)) return undefined;
  const extent = Math.max(
    position.accuracyM,
    Math.abs(offset.eastM) + focused.radiusM,
    Math.abs(offset.northM) + focused.radiusM,
    MIN_EXTENT_M,
  );
  const scale = DRAWABLE_HALF / extent;
  return { scale, target: place(offset, scale), accuracyR: position.accuracyM * scale };
}

export function usableEntry(entry: NearbyEntry): boolean {
  return (
    [entry.coordinates.latitude, entry.coordinates.longitude, entry.radiusM].every(
      Number.isFinite,
    ) && entry.radiusM >= 0
  );
}

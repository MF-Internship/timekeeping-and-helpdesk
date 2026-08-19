import type { GeofenceCoordinates, GeofenceStatus } from "./geofence";

/**
 * A guidance position snapshot lives in component memory only. It is never
 * persisted, never logged, never placed in a URL, and never sent to the backend
 * (FR-030 – FR-035).
 */
export type GuidancePosition = {
  latitude: number;
  longitude: number;
  /** Device-reported horizontal accuracy in metres, carried verbatim (FR-016). */
  accuracyM: number;
  /** ISO 8601 instant derived from the device sample timestamp. */
  capturedAt: string;
};

/**
 * The four — and only four — outcomes a browser acquisition can produce
 * (FR-008a). This vocabulary is disjoint from preview data-read failures and
 * from Attendance server rejection codes (FR-008b); no member may be added,
 * renamed, or mapped onto a server error code.
 */
export type AcquisitionErrorKind = "PERMISSION_DENIED" | "UNAVAILABLE" | "TIMEOUT" | "UNKNOWN";

export type AcquisitionStatus = "idle" | "prompting" | "acquiring" | "ready" | "error";

export type AcquisitionPermission = "unknown" | "prompt" | "granted" | "denied";

export type AcquisitionError = {
  kind: AcquisitionErrorKind;
};

export type AcquisitionState = {
  status: AcquisitionStatus;
  permission: AcquisitionPermission;
  position?: GuidancePosition;
  error?: AcquisitionError;
};

/** One ranked row of the nearby directory, derived entirely on-device. */
export type NearbyEntry = {
  /** `code` is the identity guidance carries; the row's surrogate id is never read (FR-038). */
  code: string;
  name: string;
  address: string;
  distanceM: number;
  radiusM: number;
  status: GeofenceStatus;
  /** `max(distanceM - radiusM, 0)` — an estimate, never a routing distance. */
  distanceToBoundaryM: number;
  /** `max(radiusM - distanceM, 0)`. */
  insideMarginM: number;
  /**
   * The Location's own registered coordinates, carried so the diagram can place
   * its marker relative to the position. Every distance shown as text still
   * comes from `distanceM`, which the canonical haversine produced (FR-026).
   */
  coordinates: GeofenceCoordinates;
};

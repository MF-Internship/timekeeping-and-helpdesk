import type { GuidanceEvaluation, ReferenceState } from "./guidance-state";
import type { AcquisitionError, GuidancePosition, NearbyEntry } from "./position-types";

export type GpsViewState =
  | "idle"
  | "requesting"
  | "refreshing"
  | "ready"
  | "weak"
  | "stale"
  | "unavailable";

export type GuidanceViewState = {
  gpsState: GpsViewState;
  position?: GuidancePosition;
  accuracyM?: number;
  thresholdM?: number;
  focused?: NearbyEntry;
  nearby: readonly NearbyEntry[];
  overlapCount: number;
  error?: AcquisitionError;
  referenceUnavailable: boolean;
  ageSeconds?: number;
};

type Input = {
  status: string;
  position?: GuidancePosition;
  error?: AcquisitionError;
  evaluation?: GuidanceEvaluation;
  reference: ReferenceState;
  focused?: NearbyEntry;
  isStale: boolean;
  ageSeconds?: number;
  hasResolved: boolean;
};

export function toGuidanceViewState(input: Input): GuidanceViewState {
  const evaluated = input.evaluation?.status === "evaluated" ? input.evaluation : undefined;
  const nearby = evaluated?.nearby ?? [];
  const thresholdM = evaluated?.maxAccuracyM;
  const gpsState = resolveGpsState(input, thresholdM);
  return {
    gpsState,
    position: input.position,
    accuracyM: input.position?.accuracyM,
    thresholdM,
    focused: input.focused,
    nearby,
    overlapCount: nearby.filter((entry) => entry.status === "INSIDE_GEOFENCE").length,
    error: input.error,
    referenceUnavailable: input.reference.status === "unavailable",
    ageSeconds: input.ageSeconds,
  };
}

function resolveGpsState(input: Input, thresholdM?: number): GpsViewState {
  if (input.error) return "unavailable";
  if (["prompting", "acquiring"].includes(input.status)) {
    return input.hasResolved ? "refreshing" : "requesting";
  }
  if (!input.position) return "idle";
  if (input.isStale) return "stale";
  if (thresholdM !== undefined ? input.position.accuracyM > thresholdM : false) return "weak";
  return "ready";
}

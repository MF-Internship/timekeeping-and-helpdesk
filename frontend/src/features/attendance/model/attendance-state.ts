import type { components } from "@/shared/api/schema";

import type { FreshPosition } from "./use-foreground-position";

export type LocationCandidate = components["schemas"]["LocationCandidate"];

type CanonicalFailure = {
  kind: "canonical";
  errorCode: string;
  details: Record<string, unknown>;
};

export function candidateFailure(error: unknown): LocationCandidate[] | undefined {
  if (!isCanonicalFailure(error)) return undefined;
  if (!["LOCATION_CHOICE_REQUIRED", "INVALID_LOCATION_CHOICE"].includes(error.errorCode)) {
    return undefined;
  }
  const values = error.details.location_candidates;
  return Array.isArray(values) && values.every(isCandidate)
    ? (values as LocationCandidate[])
    : undefined;
}

export async function freshCommand(
  acquire: () => Promise<FreshPosition>,
  selectedLocationId?: number,
) {
  const sample = await acquire();
  return selectedLocationId === undefined
    ? sample
    : { ...sample, selected_location_id: selectedLocationId };
}

/** Shared with the failure wording so both read the same shape (T077). */
export function isCanonicalFailure(value: unknown): value is CanonicalFailure {
  return (
    typeof value === "object" &&
    value !== null &&
    (value as { kind?: unknown }).kind === "canonical"
  );
}

function isCandidate(value: unknown): value is LocationCandidate {
  if (typeof value !== "object" || value === null) return false;
  const candidate = value as Record<string, unknown>;
  return (
    typeof candidate.id === "number" &&
    typeof candidate.code === "string" &&
    typeof candidate.name === "string" &&
    typeof candidate.distance_m === "string"
  );
}

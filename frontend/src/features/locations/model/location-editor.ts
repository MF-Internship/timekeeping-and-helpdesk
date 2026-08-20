import type { listLocations } from "@/features/locations/api/location-api";
import type { ApiFailure } from "@/shared/errors/api-error";

export type LocationRecord = Awaited<ReturnType<typeof listLocations>>[number];

export type LocationDraft = {
  id: number;
  code: string;
  version: number;
  name: string;
  address: string;
  latitude: string;
  longitude: string;
  radius_m: string;
  is_active: boolean;
  reason: string;
};

export function locationDraft(item: LocationRecord): LocationDraft {
  return {
    id: item.id,
    code: item.code,
    version: item.version,
    name: item.name,
    address: item.address,
    latitude: item.latitude,
    longitude: item.longitude,
    radius_m: item.radius_m,
    is_active: item.is_active,
    reason: "",
  };
}

export function locationUpdateBody(draft: LocationDraft, current: LocationRecord) {
  const fields = ["name", "address", "latitude", "longitude", "radius_m", "is_active"] as const;
  const changes = Object.fromEntries(
    fields.filter((field) => draft[field] !== current[field]).map((field) => [field, draft[field]]),
  );
  return {
    version: draft.version,
    ...changes,
    ...(Object.keys(changes).length && draft.reason ? { reason: draft.reason } : {}),
  };
}

export function pendingLocationUpdate(draft: LocationDraft | undefined, items: LocationRecord[]) {
  if (!draft) return undefined;
  const current = items.find((item) => item.id === draft.id);
  if (!current) return undefined;
  const body = locationUpdateBody(draft, current);
  return Object.keys(body).length === 1 ? undefined : { draft, body };
}

export function isLocationConflict(error: unknown): error is ApiFailure & { kind: "canonical" } {
  return (
    typeof error === "object" &&
    error !== null &&
    "kind" in error &&
    error.kind === "canonical" &&
    "errorCode" in error &&
    error.errorCode === "LOCATION_VERSION_CONFLICT"
  );
}

type LocationWarning = {
  readonly code: string;
  readonly related_location_codes?: readonly string[];
  readonly radius_m?: string;
  readonly threshold_m?: string;
};

export function warningText(warnings: readonly LocationWarning[]): string {
  const labels: Record<string, string> = {
    GEOFENCE_OVERLAP: "vùng địa lý chồng lấn",
    RADIUS_BELOW_ATTENDANCE_ACCURACY: "bán kính nhỏ hơn ngưỡng chính xác chấm công",
  };
  return warnings
    .map((warning) => {
      const label = labels[warning.code] ?? warning.code;
      const context: string[] = [];
      if (warning.related_location_codes?.length) {
        context.push(warning.related_location_codes.join(", "));
      }
      if (warning.radius_m && warning.threshold_m) {
        context.push(`${warning.radius_m}m / ${warning.threshold_m}m`);
      }
      return context.length ? `${label} (${context.join("; ")})` : label;
    })
    .join(", ");
}

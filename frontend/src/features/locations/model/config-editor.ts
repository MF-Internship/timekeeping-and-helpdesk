import type { ConfigUpdate, getConfig } from "@/features/locations/api/location-api";

export type ConfigValue = Awaited<ReturnType<typeof getConfig>>;

export type ConfigDraft = Omit<
  ConfigValue,
  | "id"
  | "timezone"
  | "late_grace_minutes"
  | "early_checkout_grace_minutes"
  | "late_checkout_grace_minutes"
> & {
  late_grace_minutes: string;
  early_checkout_grace_minutes: string;
  late_checkout_grace_minutes: string;
};

const TEXT_FIELDS = [
  "default_radius_m",
  "max_radius_m",
  "max_attendance_accuracy_m",
  "task_gps_good_accuracy_m",
  "task_gps_low_accuracy_m",
  "shift_start",
  "shift_end",
] as const;
const NUMBER_FIELDS = [
  "late_grace_minutes",
  "early_checkout_grace_minutes",
  "late_checkout_grace_minutes",
] as const;

export function configDraft(config: ConfigValue): ConfigDraft {
  return {
    working_weekdays: [...config.working_weekdays],
    default_radius_m: config.default_radius_m,
    max_radius_m: config.max_radius_m,
    max_attendance_accuracy_m: config.max_attendance_accuracy_m,
    task_gps_good_accuracy_m: config.task_gps_good_accuracy_m,
    task_gps_low_accuracy_m: config.task_gps_low_accuracy_m,
    shift_start: config.shift_start,
    shift_end: config.shift_end,
    late_grace_minutes: String(config.late_grace_minutes),
    early_checkout_grace_minutes: String(config.early_checkout_grace_minutes),
    late_checkout_grace_minutes: String(config.late_checkout_grace_minutes),
  };
}

export function changedConfig(config: ConfigValue, draft: ConfigDraft): ConfigUpdate {
  const entries: [string, string | number | number[]][] = [];
  for (const field of TEXT_FIELDS)
    if (draft[field] !== config[field]) entries.push([field, draft[field]]);
  for (const field of NUMBER_FIELDS) {
    const value = Number(draft[field]);
    if (value !== config[field]) entries.push([field, value]);
  }
  if (JSON.stringify(draft.working_weekdays) !== JSON.stringify(config.working_weekdays)) {
    entries.push(["working_weekdays", draft.working_weekdays]);
  }
  return Object.fromEntries(entries) as ConfigUpdate;
}

export function validationDetails(error: unknown): Record<string, string> {
  if (
    typeof error !== "object" ||
    error === null ||
    !("kind" in error) ||
    error.kind !== "canonical"
  )
    return {};
  if (!("details" in error) || typeof error.details !== "object" || error.details === null)
    return {};
  return Object.fromEntries(
    Object.entries(error.details).map(([field, value]) => [
      field,
      Array.isArray(value) ? value.join(", ") : String(value),
    ]),
  );
}

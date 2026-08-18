import { apiClient } from "@/shared/api/client";
import { parseApiResultFailure } from "@/shared/errors/api-error";

async function unwrap<T>(result: { data?: T; error?: unknown; response: Response }): Promise<T> {
  if (result.data === undefined) throw await parseApiResultFailure(result);
  return result.data;
}

async function ensureSuccess(result: { error?: unknown; response: Response }): Promise<void> {
  if (!result.response.ok) throw await parseApiResultFailure(result);
}

export async function listLocations(
  query: {
    kind?: "BUSINESS_CENTER" | "SHOP";
    parent?: number;
    is_active?: boolean;
  } = {},
) {
  return await unwrap(await apiClient.GET("/api/v1/locations/", { params: { query } }));
}

export async function updateLocation(
  locationId: number,
  body: {
    version: number;
    name?: string;
    address?: string;
    latitude?: string;
    longitude?: string;
    radius_m?: string;
    is_active?: boolean;
    reason?: string;
  },
) {
  return await unwrap(
    await apiClient.PATCH("/api/v1/locations/{location_id}/", {
      params: { path: { location_id: String(locationId) } },
      body,
    }),
  );
}

export async function getConfig() {
  return await unwrap(await apiClient.GET("/api/v1/config/"));
}

export type ConfigUpdate = {
  working_weekdays?: number[];
  default_radius_m?: string;
  max_radius_m?: string;
  max_attendance_accuracy_m?: string;
  task_gps_good_accuracy_m?: string;
  task_gps_low_accuracy_m?: string;
  shift_start?: string;
  shift_end?: string;
  late_grace_minutes?: number;
  early_checkout_grace_minutes?: number;
  late_checkout_grace_minutes?: number;
};

export async function updateConfig(body: ConfigUpdate) {
  return await unwrap(await apiClient.PATCH("/api/v1/config/", { body }));
}

export async function listHolidays() {
  return await unwrap(await apiClient.GET("/api/v1/holidays/"));
}

export async function createHoliday(body: { date: string; name: string }) {
  return await unwrap(await apiClient.POST("/api/v1/holidays/", { body }));
}

export async function deleteHoliday(holidayId: number) {
  await ensureSuccess(
    await apiClient.DELETE("/api/v1/holidays/{holiday_id}/", {
      params: { path: { holiday_id: String(holidayId) } },
    }),
  );
}

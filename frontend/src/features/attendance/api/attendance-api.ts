import { apiClient } from "@/shared/api/client";
import type { components } from "@/shared/api/schema";
import { parseApiResultFailure } from "@/shared/errors/api-error";

export type AttendanceCommand = components["schemas"]["AttendanceCommand"];
export type AttendanceCommandResult = components["schemas"]["AttendanceCommandResult"];
export type TodayAttendance = components["schemas"]["TodayAttendance"];

async function unwrap<T>(result: { data?: T; error?: unknown; response: Response }): Promise<T> {
  if (result.data === undefined) throw await parseApiResultFailure(result);
  return result.data;
}

export async function checkIn(body: AttendanceCommand) {
  return await unwrap(await apiClient.POST("/api/v1/attendance/check-in", { body }));
}

export async function checkOut(body: AttendanceCommand) {
  return await unwrap(await apiClient.POST("/api/v1/attendance/check-out", { body }));
}

export async function getTodayAttendance() {
  return await unwrap(await apiClient.GET("/api/v1/attendance/today"));
}

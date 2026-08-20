import { apiClient } from "@/shared/api/client";
import type { components } from "@/shared/api/schema";
import { parseApiResultFailure } from "@/shared/errors/api-error";

export type AttendanceReport = components["schemas"]["AttendanceReport"];
export type TaskReport = components["schemas"]["TaskReport"];

export type ReportFilters = {
  startDate: string;
  endDate: string;
  userId?: number;
};

export async function getAttendanceReport(filters: ReportFilters): Promise<AttendanceReport> {
  const result = await apiClient.GET("/api/v1/reports/attendance/", {
    params: { query: query(filters) },
  });
  if (result.data === undefined) throw await parseApiResultFailure(result);
  return result.data;
}

export async function getTaskReport(filters: ReportFilters): Promise<TaskReport> {
  const result = await apiClient.GET("/api/v1/reports/tasks/", {
    params: { query: query(filters) },
  });
  if (result.data === undefined) throw await parseApiResultFailure(result);
  return result.data;
}

function query(filters: ReportFilters) {
  return {
    start_date: filters.startDate,
    end_date: filters.endDate,
    ...(filters.userId === undefined ? {} : { user_id: filters.userId }),
  };
}


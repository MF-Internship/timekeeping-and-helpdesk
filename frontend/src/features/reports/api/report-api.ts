import { apiClient } from "@/shared/api/client";
import type { components } from "@/shared/api/schema";
import { parseApiResultFailure } from "@/shared/errors/api-error";
import { authenticatedFetch } from "@/shared/transport/authenticated-fetch";

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

export async function downloadReport(
  kind: "attendance" | "tasks",
  filters: ReportFilters,
): Promise<Blob> {
  const params = new URLSearchParams({ start_date: filters.startDate, end_date: filters.endDate });
  if (filters.userId !== undefined) params.set("user_id", String(filters.userId));
  const response = await authenticatedFetch(
    `/api/v1/reports/${kind}/export/?${params.toString()}`,
    { headers: { Accept: "text/csv" } },
  );
  if (!response.ok) throw new Error("Không thể xuất báo cáo.");
  return await response.blob();
}

import createClient from "openapi-fetch";

import type { paths } from "@/shared/api/schema";
import { authenticatedFetch } from "@/shared/transport/authenticated-fetch";

const apiClient = createClient<paths>({ fetch: authenticatedFetch });

export async function approveAttendance(attendanceId: number): Promise<unknown> {
  return apiClient.POST("/api/v1/attendance/{attendance_id}/approve/", {
    params: { path: { attendance_id: attendanceId } },
  });
}

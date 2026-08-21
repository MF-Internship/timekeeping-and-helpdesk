import { describe, expect, it, vi } from "vitest";

const client = vi.hoisted(() => ({ GET: vi.fn() }));
vi.mock("@/shared/api/client", () => ({ apiClient: client }));

import { getAttendanceReport, getTaskReport } from "@/features/reports/api/report-api";

describe("report API", () => {
  it("uses canonical report endpoints with snake_case query fields", async () => {
    client.GET.mockResolvedValue({ data: { punch_count: 0 }, response: new Response() });
    await getAttendanceReport({ startDate: "2026-08-21", endDate: "2026-08-21", userId: 5 });
    expect(client.GET).toHaveBeenCalledWith("/api/v1/reports/attendance/", {
      params: { query: { start_date: "2026-08-21", end_date: "2026-08-21", user_id: 5 } },
    });

    client.GET.mockResolvedValue({ data: { total_tasks: 0 }, response: new Response() });
    await getTaskReport({ startDate: "2026-08-21", endDate: "2026-08-21" });
    expect(client.GET).toHaveBeenCalledWith("/api/v1/reports/tasks/", {
      params: { query: { start_date: "2026-08-21", end_date: "2026-08-21" } },
    });
  });
});

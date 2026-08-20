import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

const state = vi.hoisted(() => ({
  attendance: undefined as unknown,
  tasks: undefined as unknown,
  error: undefined as unknown,
  loading: false,
  filters: { startDate: "2026-08-21", endDate: "2026-08-21" },
  refresh: vi.fn(),
}));

vi.mock("@/features/reports/model/report-state", () => ({ useReports: () => state }));

import { ReportsPanel } from "@/features/reports/ui/ReportsPanel";

describe("ReportsPanel", () => {
  it("renders canonical attendance and task metrics without coordinate export opt-in", () => {
    state.attendance = {
      users_in_open_session: 1,
      users_no_check_in_today: 2,
      users_checked_out_today: 3,
      punch_count: 4,
      total_valid_worked_minutes: 480,
      system_closed_missing_checkout_sessions: 0,
      anomaly_counts: {},
      attempt_counts: {},
      rejected_attempt_diagnostics: {},
      nearest_location_diagnostics: {},
      failure_rate: { numerator: 1, denominator: 2, excluded_count: 1, rate_percent: 50 },
    };
    state.tasks = {
      total_tasks: 5,
      status_counts: { TODO: 1, IN_PROGRESS: 1, BLOCKED: 1, COMPLETED: 2 },
      completion_method_counts: {},
      gps_quality_counts: {},
      actual_completer_counts: {},
      assigned_task_closed_count: 2,
    };

    render(<ReportsPanel />);

    expect(screen.getByText("Tỉ lệ thất bại: 50")).toBeInTheDocument();
    expect(screen.getByText("Bị loại khỏi mẫu: 1")).toBeInTheDocument();
    expect(screen.getByText("Tổng công việc: 5")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Xuất bảng công" })).not.toHaveAttribute(
      "href",
      expect.stringContaining("include_sensitive_coordinates=true"),
    );
  });
});

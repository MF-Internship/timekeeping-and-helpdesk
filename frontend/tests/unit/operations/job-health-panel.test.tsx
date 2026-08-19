import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { JobHealth } from "@/features/operations/api/job-health-api";
import { JobHealthPanel } from "@/features/operations/ui/JobHealthPanel";

const controls = vi.hoisted(() => ({
  data: undefined as JobHealth | undefined,
  error: undefined as unknown,
  refreshing: false,
  refresh: vi.fn(),
}));

vi.mock("@/features/operations/model/job-health-state", () => ({
  useJobHealth: () => controls,
}));

function health(scope: "manager" | "leader"): JobHealth {
  return {
    state: "alert",
    timezone: "Asia/Ho_Chi_Minh",
    cutoff_at: "2026-08-19T01:00:00+07:00",
    refreshed_at: "2026-08-19T01:05:00+07:00",
    latest_run: null,
    latest_successful_run: null,
    overdue_open_session_count: 2,
    evidence_counts: {
      job_closed_session_count: 1,
      missing_checkout_anomaly_count: 1,
      job_closed_without_anomaly_count: 0,
      anomaly_without_job_closed_count: 0,
    },
    invariant_valid: true,
    reason_flags: {
      no_run_history: true,
      missing_timely_success: true,
      unfinished_run: false,
      stale_running: false,
      latest_terminal_failed: false,
      run_count_mismatch: false,
      persisted_evidence_mismatch: false,
      overdue_open_sessions: true,
    },
    investigation_links: scope === "manager" ? { accounts: "/api/v1/users/" } : null,
    escalation_guidance: scope === "leader" ? "Liên hệ MANAGER để điều tra và xử lý." : null,
  };
}

describe("JobHealthPanel", () => {
  beforeEach(() => {
    controls.data = undefined;
    controls.error = undefined;
    controls.refreshing = false;
    controls.refresh.mockReset();
  });

  it("renders loading and terminal error states", () => {
    controls.refreshing = true;
    const view = render(<JobHealthPanel />);
    expect(screen.getByRole("status")).toBeInTheDocument();
    controls.refreshing = false;
    controls.error = new Error("network");
    view.rerender(<JobHealthPanel />);
    expect(screen.getByRole("alert")).toBeInTheDocument();
  });

  it("renders manager link, last-good refresh failure, and no rerun control", () => {
    controls.data = health("manager");
    controls.error = new Error("refresh failed");
    render(<JobHealthPanel />);
    expect(screen.getByRole("link", { name: "Điều tra tài khoản" })).toHaveAttribute(
      "href",
      "/api/v1/users/",
    );
    expect(screen.getByText(/dữ liệu cũ/)).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /chạy lại|rerun|repair/i }),
    ).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Làm mới" }));
    expect(controls.refresh).toHaveBeenCalledOnce();
  });

  it("renders leader escalation without account link", () => {
    controls.data = health("leader");
    render(<JobHealthPanel />);
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
    expect(screen.getByText(/Liên hệ MANAGER/)).toBeInTheDocument();
  });
});

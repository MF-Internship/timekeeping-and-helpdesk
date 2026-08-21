import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

const controls = vi.hoisted(() => ({
  capabilities: new Set(["attendance.view.self", "task.view.self", "notification.view.self"]),
  attendance: vi.fn(),
  tasks: vi.fn(),
  notifications: vi.fn(),
  attendanceReport: vi.fn(),
  taskReport: vi.fn(),
  health: vi.fn(),
}));

vi.mock("@/features/identity/model/AuthProvider", () => ({
  useAuth: () => ({ hasCapability: (capability: string) => controls.capabilities.has(capability) }),
}));
vi.mock("@/features/attendance/api/attendance-api", () => ({
  getTodayAttendance: controls.attendance,
}));
vi.mock("@/features/tasks/api/task-api", () => ({ listTasks: controls.tasks }));
vi.mock("@/features/notifications/api/notification-api", () => ({
  listNotifications: controls.notifications,
}));
vi.mock("@/features/reports/api/report-api", () => ({
  getAttendanceReport: controls.attendanceReport,
  getTaskReport: controls.taskReport,
}));
vi.mock("@/features/operations/api/job-health-api", () => ({ getJobHealth: controls.health }));

import { HomeDashboard } from "@/features/home/ui/HomeDashboard";

function resolvePrimaryResources() {
  controls.attendance.mockResolvedValue({ has_open_session: true, total_duration_minutes: 125 });
  controls.tasks.mockResolvedValue({ overdue: [], today: [], upcoming: [], completed: [] });
  controls.notifications.mockResolvedValue({ items: [], unread_count: 2 });
}

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
  controls.capabilities = new Set([
    "attendance.view.self",
    "task.view.self",
    "notification.view.self",
  ]);
});

describe("HomeDashboard", () => {
  it("shows authorized current data without requesting management resources", async () => {
    resolvePrimaryResources();
    render(<HomeDashboard />);

    expect(await screen.findByText("Đang trong ca")).toBeInTheDocument();
    expect(screen.getByText("2", { selector: "strong" })).toBeInTheDocument();
    expect(controls.attendanceReport).not.toHaveBeenCalled();
    expect(controls.taskReport).not.toHaveBeenCalled();
    expect(controls.health).not.toHaveBeenCalled();
  });

  it("keeps successful sections visible when one independent resource fails", async () => {
    resolvePrimaryResources();
    controls.notifications.mockRejectedValue(new Error("offline"));
    render(<HomeDashboard />);

    expect(await screen.findByText("Đang trong ca")).toBeInTheDocument();
    expect(await screen.findByRole("alert")).toHaveTextContent("Một phần tổng quan chưa tải được.");
  });
});

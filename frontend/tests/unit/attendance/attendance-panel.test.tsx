import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { TodayAttendance } from "@/features/attendance/api/attendance-api";
import { AttendancePanel } from "@/features/attendance/ui/AttendancePanel";

const mocks = vi.hoisted(() => ({
  getToday: vi.fn(),
  checkIn: vi.fn(),
  checkOut: vi.fn(),
  acquire: vi.fn(),
  cancel: vi.fn(),
  hasCapability: vi.fn(() => true),
}));

vi.mock("@/features/attendance/api/attendance-api", () => ({
  getTodayAttendance: mocks.getToday,
  checkIn: mocks.checkIn,
  checkOut: mocks.checkOut,
}));
vi.mock("@/features/attendance/model/use-foreground-position", () => ({
  useForegroundPosition: () => ({ acquire: mocks.acquire, cancel: mocks.cancel, loading: false }),
}));
vi.mock("@/features/identity/model/AuthProvider", () => ({
  useAuth: () => ({ hasCapability: mocks.hasCapability }),
}));

const punch = {
  id: 1,
  kind: "IN" as const,
  work_date: "2026-08-18",
  recorded_at: "2026-08-18T01:00:00Z",
  captured_at: null,
  captured_latitude: "10.000000000000000",
  captured_longitude: "106.000000000000000",
  accuracy_m: "5.000",
  location: { id: 1, code: "A", name: "Location A", address: "Address A" },
  distance_m: "0.000",
  validation_result: "INSIDE_GEOFENCE" as const,
  resolution_method: "AUTO_SINGLE" as const,
  maps_url: "https://www.google.com/maps?q=stored",
  resolved_address: "Address A",
  punch_index: 1,
};

function today(open = false, punches: TodayAttendance["punches"] = [punch]): TodayAttendance {
  return {
    work_date: "2026-08-18",
    punches,
    sessions: [],
    total_duration_minutes: "30.000000",
    has_open_session: open,
  };
}

describe("AttendancePanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.hasCapability.mockReturnValue(true);
    mocks.getToday.mockResolvedValue(today());
    mocks.acquire.mockResolvedValue({
      latitude: "10",
      longitude: "106",
      accuracy_m: "5",
      captured_at: "2026-08-18T01:00:00Z",
    });
  });
  afterEach(() => vi.useRealTimers());

  it("renders loading, unified timeline, total, safe map and refreshes after Check In", async () => {
    render(<AttendancePanel />);
    expect(screen.getByText("Đang tải…")).toBeInTheDocument();
    const button = await screen.findByRole("button", { name: "Check In" });
    const link = screen.getByRole("link", { name: "Bản đồ" });
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", "noopener noreferrer");
    fireEvent.click(button);
    await waitFor(() => expect(mocks.checkIn).toHaveBeenCalledOnce());
    await waitFor(() => expect(mocks.getToday).toHaveBeenCalledTimes(2));
    expect(screen.getByText(/30.000000/)).toBeInTheDocument();
  });

  it("keeps IN and OUT boundary locations separate in one indexed timeline", async () => {
    const out = {
      ...punch,
      id: 2,
      kind: "OUT" as const,
      punch_index: 2,
      location: { id: 2, code: "B", name: "Location B", address: "Address B" },
    };
    mocks.getToday.mockResolvedValue(today(false, [punch, out]));
    render(<AttendancePanel />);
    expect(await screen.findByText(/#1 IN.*Location A/)).toBeInTheDocument();
    expect(screen.getByText(/#2 OUT.*Location B/)).toBeInTheDocument();
  });

  it("uses Check Out for an open session and hides actions without capability", async () => {
    mocks.getToday.mockResolvedValue(today(true));
    const { rerender } = render(<AttendancePanel />);
    fireEvent.click(await screen.findByRole("button", { name: "Check Out" }));
    await waitFor(() => expect(mocks.checkOut).toHaveBeenCalledOnce());
    mocks.hasCapability.mockReturnValue(false);
    rerender(<AttendancePanel />);
    expect(screen.queryByRole("button", { name: /Check/ })).not.toBeInTheDocument();
  });

  it("renders empty and error states without artificial timers", async () => {
    vi.useFakeTimers();
    mocks.getToday.mockResolvedValue(today(false, []));
    render(<AttendancePanel />);
    await act(async () => Promise.resolve());
    expect(screen.getByText("Chưa có lượt chấm công hôm nay.")).toBeInTheDocument();
    expect(vi.getTimerCount()).toBe(0);
  });

  it("renders a canonical load failure", async () => {
    mocks.getToday.mockRejectedValue(new Error("network"));
    render(<AttendancePanel />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Không thể tải dữ liệu");
  });
});

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AttendancePanel } from "@/features/attendance/ui/AttendancePanel";

import { directoryRow, mockGeolocation, mockReference } from "../guidance/panel-harness";

const mocks = vi.hoisted(() => ({
  getToday: vi.fn(),
  checkIn: vi.fn(),
  checkOut: vi.fn(),
  acquire: vi.fn(),
  cancel: vi.fn(),
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
  useAuth: () => ({ hasCapability: () => true }),
}));
vi.mock("@/features/locations/api/location-api", () => ({
  listLocations: vi.fn(),
  getConfig: vi.fn(),
}));

const today = {
  work_date: "2026-08-20",
  punches: [],
  sessions: [],
  total_duration_minutes: "0.000000",
  has_open_session: false,
};

function precedes(first: Element, second: Element) {
  return Boolean(first.compareDocumentPosition(second) & Node.DOCUMENT_POSITION_FOLLOWING);
}

describe("Attendance experience hierarchy", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.getToday.mockResolvedValue(today);
    mocks.acquire.mockResolvedValue({
      latitude: "10",
      longitude: "106",
      accuracy_m: "8",
      captured_at: "2026-08-20T01:00:00Z",
    });
    mockReference([
      directoryRow("A", 0),
      directoryRow("B", 70),
      directoryRow("C", 80),
      directoryRow("D", 90),
    ]);
    mockGeolocation();
  });

  it("orders context, GPS, CTA, nearby support, spatial disclosure, and history semantically", async () => {
    render(<AttendancePanel />);
    const action = await screen.findByRole("button", { name: "Check In" });
    fireEvent.click(screen.getByRole("button", { name: "Xem vị trí" }));
    await screen.findByText("GPS đạt yêu cầu");

    const location = screen.getByRole("region", { name: "Địa điểm đang xem" });
    const context = screen.getByText("Sẵn sàng bắt đầu ca").closest("section")!;
    const gps = screen.getByRole("region", { name: "Vị trí thiết bị" });
    const nearby = screen.getByRole("region", { name: "Địa điểm gần bạn" });
    const spatial = screen.getByText("Sơ đồ vị trí tương đối").closest("details")!;
    const history = screen.getByRole("heading", { name: "Hôm nay" }).closest("section")!;

    expect(precedes(location, context)).toBe(true);
    expect(precedes(context, gps)).toBe(true);
    expect(precedes(gps, action)).toBe(true);
    expect(precedes(action, nearby)).toBe(true);
    expect(precedes(nearby, spatial)).toBe(true);
    expect(precedes(spatial, history)).toBe(true);
    expect(spatial).not.toHaveAttribute("open");
    expect(
      screen.getByText("Chi tiết kỹ thuật và xử lý sự cố").closest("details"),
    ).not.toHaveAttribute("open");

    fireEvent.click(screen.getByRole("button", { name: /Xem thêm 1/ }));
    expect(
      screen.getByRole("region", { name: "Địa điểm gần bạn" }).querySelectorAll("li"),
    ).toHaveLength(4);
  });

  it("keeps an authoritative rejection adjacent to a still-operable action", async () => {
    mocks.checkIn.mockRejectedValue({
      kind: "canonical",
      errorCode: "OUTSIDE_RADIUS",
      details: {},
    });
    render(<AttendancePanel />);
    const action = await screen.findByRole("button", { name: "Check In" });
    fireEvent.click(action);
    const outcome = await screen.findByRole("alert");
    expect(outcome).toHaveTextContent("Máy chủ từ chối");
    expect(precedes(action, outcome)).toBe(true);
    await waitFor(() => expect(action).toBeEnabled());
  });
});

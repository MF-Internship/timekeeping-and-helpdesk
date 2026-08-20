import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { TodayAttendance } from "@/features/attendance/api/attendance-api";
import { AttendancePanel } from "@/features/attendance/ui/AttendancePanel";

import { directoryRow, mockGeolocation, mockReference } from "../guidance/panel-harness";

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
vi.mock("@/features/locations/api/location-api", () => ({
  listLocations: vi.fn(),
  getConfig: vi.fn(),
}));

const INSIDE_ONE = "Bạn đang ở trong vùng của đúng một địa điểm đã đăng ký.";
const OUTSIDE_ALL = "Bạn đang ở ngoài vùng của mọi địa điểm gần đây.";
const AUTHORITATIVE = "Đây là kết quả chính thức từ máy chủ.";

/** Far enough north of the guidance position to sit outside a 50 m radius. */
const DISTANT_M = 500;

/**
 * The sample the punch acquires when the button is pressed. Every field differs
 * from what the guidance provider reports, so a payload built from the preview
 * would be visibly wrong rather than coincidentally right (SC-008).
 */
const PRESS_SAMPLE = {
  latitude: "20.500000000000000",
  longitude: "116.500000000000000",
  accuracy_m: "7.000",
  captured_at: "2026-08-19T09:00:00Z",
};

function canonical(errorCode: string, details: Record<string, unknown> = {}) {
  return { kind: "canonical" as const, errorCode, message: "", details, requestId: "req-1" };
}

/** Mounts the screen and opens the preview, which never runs on its own. */
async function showPreview() {
  fireEvent.click(screen.getByRole("button", { name: "Xem vị trí" }));
}

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
    sessions: [
      {
        id: 9,
        work_date: "2026-08-18",
        check_in_at: "2026-08-18T01:00:00Z",
        check_out_at: open ? null : "2026-08-18T01:30:00Z",
        check_in_location_id: 1,
        check_out_location_id: open ? null : 2,
        duration_minutes: open ? null : "30.000000",
        closed_by_job: false,
      },
    ],
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
    expect(screen.getByText("Check In thành công")).toBeInTheDocument();
    expect(screen.getByText("Tổng thời gian: 30.000000 phút")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Phiên làm việc (1)" })).toBeInTheDocument();
    expect(screen.getByText(/Location 1.*Location 2.*30.000000 phút/)).toBeInTheDocument();
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

  it("does not acquire or poll location while an open session is merely displayed", async () => {
    mocks.getToday.mockResolvedValue(today(true));
    render(<AttendancePanel />);
    expect(await screen.findByText(/Đang mở/)).toBeInTheDocument();
    expect(mocks.acquire).not.toHaveBeenCalled();
  });

  /**
   * The gate verified by T075: it is the one that already existed, unchanged.
   * An actor who may not punch still reads the whole preview, because guidance
   * is a reading and not an action (FR-037a, FR-040).
   */
  it("guidance stays fully visible to an actor without the punch capability", async () => {
    mocks.hasCapability.mockReturnValue(false);
    mockReference([directoryRow("A", 0)]);
    mockGeolocation();
    render(<AttendancePanel />);
    await screen.findByText("Tổng thời gian: 30.000000 phút");
    expect(screen.queryByRole("button", { name: /Check/ })).not.toBeInTheDocument();

    await showPreview();

    expect(await screen.findByText(INSIDE_ONE)).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Vị trí thiết bị" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Địa điểm gần bạn" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Địa điểm đang xem" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Check/ })).not.toBeInTheDocument();
  });

  /** Scenario M — the preview said inside, the server says otherwise (FR-041). */
  it("presents a server OUTSIDE_RADIUS rejection as the authoritative outcome", async () => {
    mockReference([directoryRow("A", 0)]);
    mockGeolocation();
    mocks.checkIn.mockRejectedValue(canonical("OUTSIDE_RADIUS"));
    render(<AttendancePanel />);
    const button = await screen.findByRole("button", { name: "Check In" });
    await showPreview();
    expect(await screen.findByText(INSIDE_ONE)).toBeInTheDocument();

    fireEvent.click(button);

    const outcome = await screen.findByRole("alert");
    expect(outcome).toHaveTextContent(
      "Máy chủ từ chối: vị trí đọc được lúc chấm công nằm ngoài bán kính của địa điểm.",
    );
    expect(outcome).toHaveTextContent(AUTHORITATIVE);
    expect(mocks.acquire).toHaveBeenCalledOnce();
    expect(screen.getByText(INSIDE_ONE)).toBeInTheDocument();
  });

  /** Scenario N — the preview said outside and still gated nothing (FR-040). */
  it("accepts a punch after an outside preview, which never blocked the control", async () => {
    mockReference([directoryRow("A", DISTANT_M)]);
    mockGeolocation();
    mocks.checkIn.mockResolvedValue(punch);
    render(<AttendancePanel />);
    const button = await screen.findByRole("button", { name: "Check In" });
    await showPreview();
    expect(await screen.findByText(OUTSIDE_ALL)).toBeInTheDocument();
    expect(button).toBeEnabled();

    fireEvent.click(button);

    await waitFor(() => expect(mocks.checkIn).toHaveBeenCalledOnce());
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(screen.getByText(OUTSIDE_ALL)).toBeInTheDocument();
  });

  /** The punch reads the device again at press time; the preview is not a source. */
  it("punches with the sample acquired at press time, never the guidance snapshot", async () => {
    mockReference([directoryRow("A", 0)]);
    mockGeolocation();
    mocks.checkIn.mockResolvedValue(punch);
    mocks.acquire.mockResolvedValue(PRESS_SAMPLE);
    render(<AttendancePanel />);
    const button = await screen.findByRole("button", { name: "Check In" });
    await showPreview();
    expect(await screen.findByText(INSIDE_ONE)).toBeInTheDocument();
    expect(mocks.acquire).not.toHaveBeenCalled();

    fireEvent.click(button);

    await waitFor(() => expect(mocks.checkIn).toHaveBeenCalledOnce());
    const payload = mocks.checkIn.mock.calls[0][0] as Record<string, unknown>;
    expect(payload).toEqual(PRESS_SAMPLE);
    expect(Object.keys(payload).sort()).toEqual([
      "accuracy_m",
      "captured_at",
      "latitude",
      "longitude",
    ]);
  });

  it("renders a canonical load failure", async () => {
    mocks.getToday.mockRejectedValue(new Error("network"));
    render(<AttendancePanel />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Không thể tải dữ liệu");
  });
});

import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useAttendanceExperience } from "@/features/attendance/model/use-attendance-experience";

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

const sample = {
  latitude: "10",
  longitude: "106",
  accuracy_m: "8",
  captured_at: "2026-08-20T01:00:00Z",
};
const today = (open = false) => ({
  work_date: "2026-08-20",
  punches: [],
  sessions: [],
  total_duration_minutes: "0.000000",
  has_open_session: open,
});

describe("useAttendanceExperience", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.getToday.mockResolvedValue(today());
    mocks.acquire.mockResolvedValue(sample);
  });

  it("loads today and publishes a persistent Check In success after a fresh sample", async () => {
    const { result } = renderHook(() => useAttendanceExperience());
    await waitFor(() => expect(result.current.today).toEqual(today()));

    await act(async () => result.current.punch());

    expect(mocks.acquire).toHaveBeenCalledOnce();
    expect(mocks.checkIn).toHaveBeenCalledWith(sample);
    expect(mocks.getToday).toHaveBeenCalledTimes(2);
    expect(result.current.outcome).toMatchObject({ kind: "success", action: "Check In" });
    expect(mocks.cancel).toHaveBeenCalledOnce();
  });

  it("uses Check Out for an open session", async () => {
    mocks.getToday.mockResolvedValue(today(true));
    const { result } = renderHook(() => useAttendanceExperience());
    await waitFor(() => expect(result.current.today?.has_open_session).toBe(true));
    await act(async () => result.current.punch());
    expect(mocks.checkOut).toHaveBeenCalledWith(sample);
  });

  it("keeps authoritative rejection candidates for explicit server selection", async () => {
    const candidates = [{ id: 2, code: "B", name: "Điểm B", distance_m: "2.000" }];
    mocks.checkIn.mockRejectedValue({
      kind: "canonical",
      errorCode: "LOCATION_CHOICE_REQUIRED",
      details: { location_candidates: candidates },
    });
    const { result } = renderHook(() => useAttendanceExperience());
    await waitFor(() => expect(result.current.today).toBeDefined());
    await act(async () => result.current.punch());
    expect(result.current.candidates).toEqual(candidates);
    expect(result.current.outcome).toBeUndefined();
  });
});

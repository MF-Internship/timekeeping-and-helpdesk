import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { candidateFailure, freshCommand } from "@/features/attendance/model/attendance-state";
import { AttendancePanel } from "@/features/attendance/ui/AttendancePanel";
import { LocationChoice } from "@/features/attendance/ui/LocationChoice";

import { directoryRow, mockGeolocation, mockReference } from "../guidance/panel-harness";

const candidates = [
  { id: 1, code: "A", name: "Location A", distance_m: "10.000" },
  { id: 2, code: "B", name: "Location B", distance_m: "20.000" },
];

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

/**
 * Deliberately disjoint from the guidance directory below — different ids,
 * different codes, different names. Anything the choice list borrowed from the
 * preview would therefore be visible rather than indistinguishable (FR-042).
 */
const SERVER_CANDIDATES = [
  { id: 7, code: "C", name: "Location C", distance_m: "12.000" },
  { id: 8, code: "D", name: "Location D", distance_m: "18.000" },
];

const EMPTY_TODAY = {
  work_date: "2026-08-19",
  punches: [],
  sessions: [],
  total_duration_minutes: "0.000000",
  has_open_session: false,
};

describe("Location choice", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.getToday.mockResolvedValue(EMPTY_TODAY);
    mocks.acquire.mockResolvedValue({
      latitude: "10",
      longitude: "106",
      accuracy_m: "5",
      captured_at: "2026-08-19T09:00:00Z",
    });
  });

  /**
   * Scenario P — focusing a Location in the preview is display state and reaches
   * neither the punch nor the choice that follows it. The server decides which
   * Locations are candidates, and the answer is chosen from that set alone.
   */
  it("offers the server's own candidate set after a focused preview target", async () => {
    mockReference([directoryRow("A", 0), directoryRow("B", 10)]);
    mockGeolocation();
    mocks.checkIn.mockRejectedValue({
      kind: "canonical",
      errorCode: "LOCATION_CHOICE_REQUIRED",
      message: "",
      details: { location_candidates: SERVER_CANDIDATES },
    });
    render(<AttendancePanel />);
    const button = await screen.findByRole("button", { name: "Check In" });
    fireEvent.click(screen.getByRole("button", { name: "Xem vị trí" }));
    const focus = await screen.findByRole("radio", { name: /^B —/ });
    fireEvent.click(focus);
    expect(focus).toBeChecked();

    fireEvent.click(button);

    const choice = await screen.findByRole("region", { name: "Chọn địa điểm chấm công" });
    expect(
      within(choice)
        .getAllByRole("listitem")
        .map((item) => item.textContent),
    ).toEqual(["Location C — 12.000 mChọn", "Location D — 18.000 mChọn"]);
    expect(within(choice).queryByText(/Điểm [AB]/)).not.toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();

    fireEvent.click(within(choice).getAllByRole("button", { name: "Chọn" })[0]);

    await waitFor(() => expect(mocks.checkIn).toHaveBeenCalledTimes(2));
    expect(mocks.acquire).toHaveBeenCalledTimes(2);
    expect(mocks.checkIn.mock.calls[1][0]).toMatchObject({ selected_location_id: 7 });
  });

  it("renders the latest candidates and selects by server id", () => {
    const onSelect = vi.fn();
    render(<LocationChoice candidates={candidates} disabled={false} onSelect={onSelect} />);
    fireEvent.click(screen.getAllByRole("button", { name: "Chọn" })[1]);
    expect(onSelect).toHaveBeenCalledWith(2);
  });

  it("extracts both choice-required and invalid-choice replacement lists", () => {
    for (const errorCode of ["LOCATION_CHOICE_REQUIRED", "INVALID_LOCATION_CHOICE"]) {
      expect(
        candidateFailure({
          kind: "canonical",
          errorCode,
          details: { location_candidates: candidates },
        }),
      ).toEqual(candidates);
    }
  });

  it("acquires a new GPS sample before every selected-id resubmission", async () => {
    const acquire = vi.fn().mockResolvedValue({
      latitude: "10",
      longitude: "106",
      accuracy_m: "5",
      captured_at: "2026-08-18T00:00:00Z",
    });
    await freshCommand(acquire);
    const selected = await freshCommand(acquire, 2);
    expect(acquire).toHaveBeenCalledTimes(2);
    expect("selected_location_id" in selected && selected.selected_location_id).toBe(2);
  });
});

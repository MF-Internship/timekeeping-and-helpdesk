import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { PrimaryAttendanceAction } from "@/features/attendance/ui/PrimaryAttendanceAction";

const capability = vi.fn();
vi.mock("@/features/identity/model/AuthProvider", () => ({
  useAuth: () => ({ hasCapability: capability }),
}));
const today = {
  work_date: "2026-08-20",
  punches: [],
  sessions: [],
  total_duration_minutes: "0.000000",
  has_open_session: false,
};

describe("PrimaryAttendanceAction", () => {
  it("uses the action-specific capability and label", () => {
    capability.mockImplementation((value) => value === "attendance.check_in.self");
    const punch = vi.fn();
    render(<PrimaryAttendanceAction today={today} busy={false} onPunch={punch} />);
    fireEvent.click(screen.getByRole("button", { name: "Check In" }));
    expect(punch).toHaveBeenCalledOnce();
  });

  it("uses an action-specific busy label and prevents duplicates", () => {
    capability.mockReturnValue(true);
    render(
      <PrimaryAttendanceAction
        today={{ ...today, has_open_session: true }}
        busy
        onPunch={vi.fn()}
      />,
    );
    expect(screen.getByRole("button", { name: "Đang Check Out" })).toBeDisabled();
  });

  it("renders no implied action without capability", () => {
    capability.mockReturnValue(false);
    render(<PrimaryAttendanceAction today={today} busy={false} onPunch={vi.fn()} />);
    expect(screen.queryByRole("button", { name: "Check In" })).toBeNull();
  });
});

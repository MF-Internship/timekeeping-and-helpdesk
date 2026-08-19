import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AttendanceContextHeader } from "@/features/attendance/ui/AttendanceContextHeader";

const today = {
  work_date: "2026-08-20",
  punches: [],
  sessions: [],
  total_duration_minutes: "0.000000",
  has_open_session: false,
};

describe("AttendanceContextHeader", () => {
  it("changes the headline for Check In and Check Out context", () => {
    const { rerender } = render(<AttendanceContextHeader today={today} />);
    expect(screen.getByRole("heading", { name: "Sẵn sàng bắt đầu ca" })).toBeVisible();
    rerender(<AttendanceContextHeader today={{ ...today, has_open_session: true }} />);
    expect(screen.getByRole("heading", { name: "Đang trong ca làm việc" })).toBeVisible();
  });
});

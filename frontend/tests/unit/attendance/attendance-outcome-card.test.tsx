import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { AttendanceOutcomeCard } from "@/features/attendance/ui/AttendanceOutcomeCard";

describe("AttendanceOutcomeCard", () => {
  it("keeps successful action and updated-state copy in a status", () => {
    render(
      <AttendanceOutcomeCard
        outcome={{
          kind: "success",
          action: "Check In",
          message: "Check In đã hoàn tất. Trạng thái ca làm việc đã được cập nhật.",
        }}
        onRetry={vi.fn()}
      />,
    );
    expect(screen.getByRole("status")).toHaveTextContent("Check In thành công");
    expect(screen.getByRole("status")).toHaveTextContent("đã được cập nhật");
  });

  it("presents authoritative rejection, next step, and retry", () => {
    const retry = vi.fn();
    render(
      <AttendanceOutcomeCard
        outcome={{ kind: "rejection", message: "Máy chủ từ chối: GPS yếu." }}
        onRetry={retry}
      />,
    );
    expect(screen.getByRole("alert")).toHaveTextContent("Đây là kết quả chính thức từ máy chủ");
    fireEvent.click(screen.getByRole("button", { name: "Thử lại với GPS mới" }));
    expect(retry).toHaveBeenCalledOnce();
  });
});

import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { GuidanceStateNotice } from "@/features/guidance/ui/GuidanceStateNotice";

describe("GuidanceStateNotice", () => {
  it.each([
    ["PERMISSION_DENIED", "Quyền vị trí đã bị từ chối"],
    ["UNAVAILABLE", "GPS không khả dụng"],
    ["TIMEOUT", "Quá thời gian lấy GPS"],
    ["UNKNOWN", "Không lấy được GPS"],
  ] as const)("keeps %s recovery distinct", (kind, title) => {
    const retry = vi.fn();
    render(<GuidanceStateNotice error={{ kind }} onRetry={retry} />);
    expect(screen.getByRole("alert")).toHaveTextContent(title);
    fireEvent.click(screen.getByRole("button", { name: "Thử lấy vị trí lại" }));
    expect(retry).toHaveBeenCalledOnce();
  });
});

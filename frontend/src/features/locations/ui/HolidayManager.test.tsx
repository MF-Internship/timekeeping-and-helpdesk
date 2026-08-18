import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { HolidayManager } from "./HolidayManager";

const controls = vi.hoisted(() => ({
  canManage: false,
  list: vi.fn(),
  create: vi.fn(),
  remove: vi.fn(),
}));
vi.mock("@/features/identity/model/AuthProvider", () => ({
  useAuth: () => ({ hasCapability: () => controls.canManage }),
}));
vi.mock("@/features/locations/api/location-api", () => ({
  listHolidays: controls.list,
  createHoliday: controls.create,
  deleteHoliday: controls.remove,
}));
afterEach(() => {
  cleanup();
  vi.clearAllMocks();
  controls.canManage = false;
});

describe("HolidayManager", () => {
  it("renders a load failure without an unhandled rejection", async () => {
    controls.canManage = true;
    controls.list.mockRejectedValue(new Error("network"));
    render(<HolidayManager />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Không thể tải");
  });

  it("is Manager-only", () => {
    render(<HolidayManager />);
    expect(screen.getByText(/không có quyền/)).toBeInTheDocument();
    expect(controls.list).not.toHaveBeenCalled();
  });

  it("confirms delete and refreshes a missing target", async () => {
    controls.canManage = true;
    controls.list.mockResolvedValue([{ id: 1, date: "2027-01-01", name: "New year" }]);
    controls.remove.mockRejectedValue(new Error("missing"));
    vi.spyOn(window, "confirm").mockReturnValue(true);
    render(<HolidayManager />);
    fireEvent.click(await screen.findByRole("button", { name: "Xóa" }));
    await waitFor(() => expect(controls.remove).toHaveBeenCalledWith(1));
    expect(await screen.findByRole("alert")).toHaveTextContent("danh sách đã được làm mới");
  });
});

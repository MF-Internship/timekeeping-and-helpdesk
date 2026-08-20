import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { LocationDirectory } from "./LocationDirectory";

const controls = vi.hoisted(() => ({
  capabilities: new Set<string>(),
  list: vi.fn(),
  update: vi.fn(),
}));
vi.mock("@/features/identity/model/AuthProvider", () => ({
  useAuth: () => ({ hasCapability: (value: string) => controls.capabilities.has(value) }),
}));
vi.mock("@/features/locations/api/location-api", () => ({
  listLocations: controls.list,
  updateLocation: controls.update,
}));

const item = {
  id: 1,
  code: "SHOP1",
  name: "Shop",
  kind: "SHOP",
  parent_id: null,
  parent_code: null,
  address: "Address",
  latitude: "10.000000000000000",
  longitude: "106.000000000000000",
  radius_m: "50.000",
  is_active: true,
  version: 1,
};
const conflict = {
  kind: "canonical",
  errorCode: "LOCATION_VERSION_CONFLICT",
  message: "Conflict",
  details: { current_version: 2, submitted_reason: "Giữ nội dung" },
  requestId: "00000000-0000-4000-8000-000000000000",
};
const relatedLocationId = Number("2");
const overlapWarning = {
  code: "GEOFENCE_OVERLAP",
  related_location_ids: [relatedLocationId],
  related_location_codes: ["SHOP2"],
  radius_m: "20.000",
  threshold_m: "25.000",
};

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
  controls.capabilities = new Set();
});

async function openLocationEditor() {
  fireEvent.click(await screen.findByRole("button", { name: "Chỉnh sửa SHOP1" }));
}

describe("LocationDirectory", () => {
  it("renders a load failure without an unhandled rejection", async () => {
    controls.list.mockRejectedValue(new Error("network"));
    render(<LocationDirectory />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Không thể tải");
  });

  it("shows the complete directory and all filters without Manager controls", async () => {
    controls.list.mockResolvedValue([item]);
    render(<LocationDirectory />);
    expect(await screen.findByText(/SHOP1/)).toBeInTheDocument();
    expect(screen.getByText(/10\.000000000000000/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Chỉnh sửa SHOP1" })).toBeNull();
    fireEvent.change(screen.getByLabelText("Loại địa điểm"), { target: { value: "SHOP" } });
    fireEvent.change(screen.getByLabelText("Mã cha"), { target: { value: "7" } });
    fireEvent.change(screen.getByLabelText("Trạng thái"), { target: { value: "false" } });
    await waitFor(() =>
      expect(controls.list).toHaveBeenLastCalledWith({
        kind: "SHOP",
        parent: 7,
        is_active: false,
      }),
    );
  });

  it("lets a Manager edit mutable fields and displays warning-success", async () => {
    controls.capabilities.add("location.manage");
    controls.list.mockResolvedValue([item]);
    controls.update.mockResolvedValueOnce({
      location: { ...item, name: "Shop mới", version: 2 },
      warnings: [overlapWarning],
    });
    render(<LocationDirectory />);
    await openLocationEditor();
    fireEvent.change(screen.getByLabelText("Tên địa điểm"), { target: { value: "Shop mới" } });
    fireEvent.change(screen.getByLabelText("Lý do thay đổi"), {
      target: { value: "Chuẩn hóa tên" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Lưu địa điểm" }));
    await waitFor(() =>
      expect(controls.update).toHaveBeenCalledWith(1, {
        version: 1,
        name: "Shop mới",
        reason: "Chuẩn hóa tên",
      }),
    );
    const notice = await screen.findByRole("status");
    expect(notice).toHaveTextContent("vùng địa lý chồng lấn");
    expect(notice).toHaveTextContent("SHOP2");
    expect(notice).toHaveTextContent("20.000m / 25.000m");
  });

  it("does not claim a save when the Location draft is unchanged", async () => {
    controls.capabilities.add("location.manage");
    controls.list.mockResolvedValue([item]);
    render(<LocationDirectory />);
    await openLocationEditor();
    fireEvent.click(screen.getByRole("button", { name: "Lưu địa điểm" }));
    expect(await screen.findByRole("status")).toHaveTextContent("Không có thay đổi");
    expect(controls.update).not.toHaveBeenCalled();
  });

  it("refreshes the server version while preserving a stale draft and reason", async () => {
    controls.capabilities.add("location.manage");
    controls.list.mockResolvedValueOnce([item]).mockResolvedValueOnce([{ ...item, version: 2 }]);
    controls.update
      .mockRejectedValueOnce(conflict)
      .mockResolvedValueOnce({ location: { ...item, name: "Bản nháp", version: 3 }, warnings: [] });
    render(<LocationDirectory />);
    await openLocationEditor();
    fireEvent.change(screen.getByLabelText("Tên địa điểm"), { target: { value: "Bản nháp" } });
    fireEvent.change(screen.getByLabelText("Lý do thay đổi"), {
      target: { value: "Giữ nội dung" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Lưu địa điểm" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("phiên bản 2");
    expect(screen.getByLabelText("Tên địa điểm")).toHaveValue("Bản nháp");
    expect(screen.getByLabelText("Lý do thay đổi")).toHaveValue("Giữ nội dung");
    fireEvent.click(screen.getByRole("button", { name: "Lưu địa điểm" }));
    await waitFor(() => expect(controls.update.mock.calls[1]?.[1].version).toBe(2));
  });
});

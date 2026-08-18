import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ConfigEditor } from "./ConfigEditor";

const controls = vi.hoisted(() => ({ canManage: false, get: vi.fn(), update: vi.fn() }));
vi.mock("@/features/identity/model/AuthProvider", () => ({
  useAuth: () => ({ hasCapability: () => controls.canManage }),
}));
vi.mock("@/features/locations/api/location-api", () => ({
  getConfig: controls.get,
  updateConfig: controls.update,
}));
const config = {
  id: 1,
  timezone: "Asia/Ho_Chi_Minh",
  working_weekdays: [0, 1, 2, 3, 4, 5],
  default_radius_m: "50.000",
  max_radius_m: "70.000",
  max_attendance_accuracy_m: "25.000",
  task_gps_good_accuracy_m: "25.000",
  task_gps_low_accuracy_m: "100.000",
  shift_start: "08:00:00",
  shift_end: "17:00:00",
  late_grace_minutes: 15,
  early_checkout_grace_minutes: 10,
  late_checkout_grace_minutes: 60,
};
const affectedLocationId = Number("7");
afterEach(() => {
  cleanup();
  vi.clearAllMocks();
  controls.canManage = false;
});

describe("ConfigEditor", () => {
  it("renders a load failure without an unhandled rejection", async () => {
    controls.get.mockRejectedValue(new Error("network"));
    render(<ConfigEditor />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Không thể tải");
  });

  it("lets every role read independent thresholds but hides editor", async () => {
    controls.get.mockResolvedValue(config);
    render(<ConfigEditor />);
    expect(await screen.findByText(/25.000\/100.000/)).toBeInTheDocument();
    expect(screen.getByText(/Thứ Hai.*Thứ Bảy/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Lưu cấu hình" })).toBeNull();
  });

  it("lets a Manager update independent values and shows warning-success", async () => {
    controls.canManage = true;
    controls.get.mockResolvedValue(config);
    controls.update.mockResolvedValue({
      config: { ...config, max_attendance_accuracy_m: "30.000" },
      warnings: [
        {
          code: "RADIUS_BELOW_ATTENDANCE_ACCURACY",
          related_location_ids: [affectedLocationId],
          related_location_codes: ["SHOP7"],
          radius_m: "20.000",
          threshold_m: "30.000",
        },
      ],
    });
    render(<ConfigEditor />);
    fireEvent.change(await screen.findByLabelText("Độ chính xác chấm công tối đa (m)"), {
      target: { value: "30.000" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Lưu cấu hình" }));
    await waitFor(() =>
      expect(controls.update).toHaveBeenCalledWith({ max_attendance_accuracy_m: "30.000" }),
    );
    const notice = await screen.findByRole("status");
    expect(notice).toHaveTextContent("bán kính nhỏ hơn ngưỡng");
    expect(notice).toHaveTextContent("SHOP7");
    expect(notice).toHaveTextContent("20.000m / 30.000m");
  });

  it("does not claim a save when the Config draft is unchanged", async () => {
    controls.canManage = true;
    controls.get.mockResolvedValue(config);
    render(<ConfigEditor />);
    fireEvent.click(await screen.findByRole("button", { name: "Lưu cấu hình" }));
    expect(await screen.findByRole("status")).toHaveTextContent("Không có thay đổi");
    expect(controls.update).not.toHaveBeenCalled();
  });
});

describe("ConfigEditor validation", () => {
  it("renders server validation beside the invalid field and keeps the draft", async () => {
    controls.canManage = true;
    controls.get.mockResolvedValue(config);
    controls.update.mockRejectedValue({
      kind: "canonical",
      errorCode: "VALIDATION_FAILED",
      message: "Invalid",
      details: { max_radius_m: ["SHOP1", "SHOP2"] },
      requestId: "00000000-0000-4000-8000-000000000000",
    });
    render(<ConfigEditor />);
    fireEvent.change(await screen.findByLabelText("Bán kính tối đa (m)"), {
      target: { value: "40.000" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Lưu cấu hình" }));
    expect(await screen.findByText(/SHOP1, SHOP2/)).toBeInTheDocument();
    expect(screen.getByLabelText(/^Bán kính tối đa \(m\)/)).toHaveValue(40);
  });

  it("maps every cross-field validation category beside its owning control", async () => {
    controls.canManage = true;
    controls.get.mockResolvedValue(config);
    controls.update.mockRejectedValue({
      kind: "canonical",
      errorCode: "VALIDATION_FAILED",
      message: "Invalid",
      details: {
        default_radius_m: ["radius-order"],
        task_gps_good_accuracy_m: ["task-order"],
        working_weekdays: ["weekdays"],
        shift_start: ["shift-order"],
        late_grace_minutes: ["negative-grace"],
        max_attendance_accuracy_m: ["non-finite-meter"],
      },
      requestId: "00000000-0000-4000-8000-000000000000",
    });
    render(<ConfigEditor />);
    fireEvent.change(await screen.findByLabelText("Bán kính mặc định (m)"), {
      target: { value: "60.000" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Lưu cấu hình" }));
    for (const message of [
      "radius-order",
      "task-order",
      "weekdays",
      "shift-order",
      "negative-grace",
      "non-finite-meter",
    ]) {
      expect(await screen.findByText(message)).toBeInTheDocument();
    }
    expect(screen.getByLabelText("Bán kính mặc định (m)")).toHaveValue(60);
  });

  it("submits the selected working weekdays", async () => {
    controls.canManage = true;
    controls.get.mockResolvedValue(config);
    controls.update.mockResolvedValue({
      config: { ...config, working_weekdays: [0, 1, 2, 3, 4] },
      warnings: [],
    });
    render(<ConfigEditor />);
    fireEvent.click(await screen.findByLabelText("Thứ Bảy"));
    fireEvent.click(screen.getByRole("button", { name: "Lưu cấu hình" }));
    await waitFor(() =>
      expect(controls.update).toHaveBeenCalledWith({ working_weekdays: [0, 1, 2, 3, 4] }),
    );
  });
});

import { fireEvent, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  advance,
  CAPTURED_AT,
  directoryRow,
  mockGeolocation,
  mockReference,
  nearbyRegion,
  pressRefresh,
  renderPanel,
} from "./panel-harness";

vi.mock("@/features/locations/api/location-api", () => ({
  listLocations: vi.fn(),
  getConfig: vi.fn(),
}));

describe("guidance experience", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(CAPTURED_AT);
  });
  afterEach(() => vi.useRealTimers());

  it("keeps the operational answer primary and details progressively disclosed", async () => {
    mockReference([
      directoryRow("A", 0),
      directoryRow("B", 70),
      directoryRow("C", 80),
      directoryRow("D", 90),
    ]);
    const device = mockGeolocation();
    await renderPanel();

    expect(screen.getByText("GPS đạt yêu cầu")).toBeVisible();
    expect(screen.getByRole("region", { name: "Địa điểm đang xem" })).toHaveTextContent("A");
    expect(screen.getByText("Chi tiết GPS").closest("details")).not.toHaveAttribute("open");
    expect(screen.getByText("Sơ đồ vị trí tương đối").closest("details")).not.toHaveAttribute(
      "open",
    );

    const nearby = nearbyRegion();
    expect(within(nearby).getAllByRole("listitem")).toHaveLength(3);
    fireEvent.click(within(nearby).getByRole("button", { name: /Xem thêm 1/ }));
    expect(within(nearby).getAllByRole("listitem")).toHaveLength(4);

    await pressRefresh();
    expect(device.geolocation.watchPosition).toHaveBeenCalledTimes(2);
  });

  it("distinguishes weak, outside, and stale preview states", async () => {
    mockReference([directoryRow("A", 500)]);
    mockGeolocation({ northM: 0, accuracyM: 150, timestamp: CAPTURED_AT });
    await renderPanel();

    expect(screen.getByText("GPS chưa đủ chính xác")).toBeVisible();
    expect(screen.getByText(/ngoài vùng của mọi địa điểm/)).toBeVisible();

    await advance(61_000);
    expect(screen.getByText("Bản xem trước đã cũ")).toBeVisible();
    expect(screen.getByText(/chấm công, hệ thống sẽ đọc lại vị trí mới/i)).toBeVisible();
  });

  it("keeps overlapping candidates visible while focus remains presentation-only", async () => {
    mockReference([
      directoryRow("A", 0),
      directoryRow("B", 0),
      directoryRow("C", 1),
      directoryRow("D", 70),
    ]);
    mockGeolocation();
    await renderPanel();

    expect(screen.getByText("Có 3 địa điểm chồng lấn")).toBeVisible();
    const nearby = nearbyRegion();
    expect(within(nearby).getAllByRole("listitem")).toHaveLength(3);
    fireEvent.click(within(nearby).getByRole("radio", { name: "B — Điểm B" }));
    expect(screen.getByRole("region", { name: "Địa điểm đang xem" })).toHaveTextContent("Điểm B");
    expect(screen.getByText(/Bản xem trước này không chọn thay bạn/i)).toBeVisible();
  });
});

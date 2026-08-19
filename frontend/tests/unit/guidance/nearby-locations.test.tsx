import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { NearbyEntry } from "@/features/guidance/model/position-types";
import { NearbyLocations } from "@/features/guidance/ui/NearbyLocations";

function entry(code: string, status: NearbyEntry["status"], distanceM: number): NearbyEntry {
  return {
    code,
    name: `Điểm ${code}`,
    address: `Địa chỉ ${code}`,
    distanceM,
    radiusM: 50,
    status,
    distanceToBoundaryM: Math.max(distanceM - 50, 0),
    insideMarginM: Math.max(50 - distanceM, 0),
    coordinates: { latitude: 10, longitude: 106 },
  };
}

describe("NearbyLocations", () => {
  it("renders an intentional empty state", () => {
    render(<NearbyLocations entries={[]} onFocus={vi.fn()} />);
    expect(screen.getByRole("region", { name: "Địa điểm gần bạn" })).toHaveTextContent(
      "Không có địa điểm đang hoạt động",
    );
  });

  it("keeps canonical order, all containing rows, and a three-row floor", () => {
    const entries = [
      entry("A", "INSIDE_GEOFENCE", 1),
      entry("B", "OUTSIDE_GEOFENCE", 60),
      entry("C", "INSIDE_GEOFENCE", 2),
      entry("D", "OUTSIDE_GEOFENCE", 70),
    ];
    render(<NearbyLocations entries={entries} focusedCode="A" onFocus={vi.fn()} />);
    const rows = within(screen.getByRole("region", { name: "Địa điểm gần bạn" })).getAllByRole(
      "listitem",
    );
    expect(rows.map((row) => row.textContent?.slice(0, 1))).toEqual(["A", "B", "C"]);
    expect(screen.getByRole("button", { name: /Xem thêm 1/ })).toBeVisible();
  });

  it("reveals and collapses extras without hiding containing Locations", () => {
    const entries = [
      entry("A", "INSIDE_GEOFENCE", 1),
      entry("B", "INSIDE_GEOFENCE", 2),
      entry("C", "INSIDE_GEOFENCE", 3),
      entry("D", "OUTSIDE_GEOFENCE", 60),
    ];
    render(<NearbyLocations entries={entries} focusedCode="A" onFocus={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: /Xem thêm/ }));
    expect(screen.getAllByRole("listitem")).toHaveLength(4);
    fireEvent.click(screen.getByRole("button", { name: "Thu gọn" }));
    expect(screen.getAllByRole("listitem")).toHaveLength(3);
  });
});

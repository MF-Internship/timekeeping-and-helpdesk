import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { NearbyEntry } from "@/features/guidance/model/position-types";
import { LocationSummaryCard } from "@/features/guidance/ui/LocationSummaryCard";
import { NearbyLocations } from "@/features/guidance/ui/NearbyLocations";

function containing(code: string, distanceM: number): NearbyEntry {
  return {
    code,
    name: `Điểm ${code}`,
    address: `Địa chỉ ${code}`,
    distanceM,
    radiusM: 50,
    status: "INSIDE_GEOFENCE",
    distanceToBoundaryM: 0,
    insideMarginM: 50 - distanceM,
    coordinates: { latitude: 10, longitude: 106 },
  };
}

describe("overlapping Locations", () => {
  it("keeps every containing row and makes nearest only the visual fallback", () => {
    const focus = vi.fn();
    const entries = [containing("A", 0), containing("B", 0), containing("C", 2)];
    render(<NearbyLocations entries={entries} focusedCode="A" onFocus={focus} />);

    expect(screen.getAllByRole("listitem")).toHaveLength(3);
    expect(screen.getByRole("radio", { name: "A — Điểm A" })).toBeChecked();
    fireEvent.click(screen.getByRole("radio", { name: "B — Điểm B" }));
    expect(focus).toHaveBeenCalledWith("B");
  });

  it("labels overlap as information without hiding the focused Location", () => {
    render(<LocationSummaryCard location={containing("A", 0)} overlapCount={3} />);
    const summary = screen.getByRole("region", { name: "Địa điểm đang xem" });
    expect(within(summary).getByText("Có 3 địa điểm chồng lấn")).toBeVisible();
    expect(summary).toHaveTextContent("Chỉ thay đổi nội dung xem trước");
  });
});

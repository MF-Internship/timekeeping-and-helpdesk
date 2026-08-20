import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { NearbyEntry } from "@/features/guidance/model/position-types";
import { LocationSummaryCard } from "@/features/guidance/ui/LocationSummaryCard";

const entry: NearbyEntry = {
  code: "HCM001",
  name: "Cửa hàng Quận 1",
  address: "1 Nguyễn Huệ",
  distanceM: 12,
  radiusM: 25,
  status: "INSIDE_GEOFENCE",
  distanceToBoundaryM: 0,
  insideMarginM: 13,
  coordinates: { latitude: 10, longitude: 106 },
};

describe("LocationSummaryCard", () => {
  it("shows a coherent Location summary without raw coordinates", () => {
    render(<LocationSummaryCard location={entry} />);
    const region = screen.getByRole("region", { name: "Địa điểm đang xem" });
    expect(region).toHaveTextContent("HCM001");
    expect(region).toHaveTextContent("1 Nguyễn Huệ");
    expect(region).toHaveTextContent("12.0 m");
    expect(region).toHaveTextContent("25.0 m");
    expect(region).toHaveTextContent("Trong vùng");
    expect(region).not.toHaveTextContent("10.000000");
  });

  it("presents overlap as information, not an alert", () => {
    render(<LocationSummaryCard location={entry} overlapCount={2} />);
    expect(screen.getByText("Có 2 địa điểm chồng lấn")).toBeVisible();
    expect(screen.queryByRole("alert")).toBeNull();
  });
});

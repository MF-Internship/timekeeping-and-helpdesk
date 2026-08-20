import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { LocationDiagnostics } from "@/features/guidance/ui/LocationDiagnostics";

describe("LocationDiagnostics", () => {
  it("keeps coordinates, time, radius, and precise distance in a closed disclosure", () => {
    render(
      <LocationDiagnostics
        position={{
          latitude: 10,
          longitude: 106,
          accuracyM: 14,
          capturedAt: "2026-08-20T00:00:00Z",
        }}
        focused={{
          code: "A",
          name: "A",
          address: "A",
          distanceM: 12,
          radiusM: 25,
          status: "INSIDE_GEOFENCE",
          distanceToBoundaryM: 0,
          insideMarginM: 13,
          coordinates: { latitude: 10, longitude: 106 },
        }}
      />,
    );
    const disclosure = screen.getByText("Chi tiết kỹ thuật và xử lý sự cố").closest("details");
    expect(disclosure).not.toHaveAttribute("open");
    expect(disclosure).toHaveTextContent("Vĩ độ: 10.000000");
    expect(disclosure).toHaveTextContent("Khoảng cách chính xác: 12.0 m");
    expect(disclosure).toHaveTextContent("Bán kính cấu hình: 25.0 m");
  });
});

import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { GpsStatusCard } from "@/features/guidance/ui/GpsStatusCard";

const position = {
  latitude: 10,
  longitude: 106,
  accuracyM: 14,
  capturedAt: "2026-08-20T00:00:00Z",
};

describe("GpsStatusCard", () => {
  it("pairs numeric ready status and threshold with text and a non-color cue", () => {
    render(
      <GpsStatusCard
        state="ready"
        position={position}
        thresholdM={25}
        ageSeconds={2}
        onRefresh={vi.fn()}
      />,
    );
    const status = screen.getByRole("region", { name: "Vị trí thiết bị" });
    expect(status).toHaveTextContent("Sai số hiện tại: 14.0 m");
    expect(status).toHaveTextContent("Ngưỡng sai số cho phép khi chấm công: 25.0 m");
    expect(status).toHaveTextContent("GPS đạt yêu cầu");
  });

  it.each([
    ["weak", "GPS chưa đủ chính xác"],
    ["refreshing", "Đang làm mới GPS"],
    ["stale", "Bản xem trước đã cũ"],
    ["unavailable", "Không lấy được GPS"],
  ] as const)("renders %s with explicit text", (state, label) => {
    render(
      <GpsStatusCard
        state={state}
        position={state === "unavailable" ? undefined : position}
        thresholdM={25}
        ageSeconds={61}
        onRefresh={vi.fn()}
      />,
    );
    expect(screen.getByRole("region", { name: "Vị trí thiết bị" })).toHaveTextContent(label);
  });

  it("announces busy state and disables duplicate refresh", () => {
    const refresh = vi.fn();
    render(
      <GpsStatusCard state="refreshing" position={position} thresholdM={25} onRefresh={refresh} />,
    );
    expect(screen.getByRole("region", { name: "Vị trí thiết bị" })).toHaveAttribute(
      "aria-busy",
      "true",
    );
    fireEvent.click(screen.getByRole("button", { name: "Làm mới vị trí" }));
    expect(refresh).not.toHaveBeenCalled();
  });
});

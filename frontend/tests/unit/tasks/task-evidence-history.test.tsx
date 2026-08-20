import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { TaskManagementPanel } from "@/features/tasks/ui/TaskManagementPanel";

import { groupedFixture, managementFixture, taskFixture } from "./fixtures";

const controls = vi.hoisted(() => ({ management: {} as Record<string, unknown> }));
vi.mock("@/features/tasks/model/use-task-management", () => ({
  useTaskManagement: () => controls.management,
}));

describe("Task evidence presentation", () => {
  it("shows the Location-derived address and exact server Maps URL safely", async () => {
    const mapsUrl = "https://www.google.com/maps?q=10.123456789012345%2C106.987654321098765";
    controls.management = managementFixture({
      loadState: { kind: "ready", data: groupedFixture({ today: [taskFixture()] }) },
      detail: vi.fn().mockResolvedValue({
        ...taskFixture(),
        updates: [
          {
            id: 5,
            actor: { id: 3, full_name: "An" },
            status: "COMPLETED",
            recorded_at: "2026-08-20T08:00:00Z",
            note: null,
            block_reason: null,
            completion_method: "FIELD_EVIDENCE",
            completion_note: null,
            captured_latitude: "10.123456789012345",
            captured_longitude: "106.987654321098765",
            accuracy_m: "12",
            captured_at: "2026-08-20T08:00:00Z",
            gps_quality: "GOOD",
            actual_location_id: 3,
            actual_location: {
              id: 3,
              code: "HCM",
              name: "ignored",
              is_active: true,
              address: "ignored",
            },
            validation_result: "INSIDE_GEOFENCE",
            resolution_method: "AUTO_SINGLE",
            distance_m: "1",
            location_candidates: [3],
            photos: [{ id: 8, mime: "image/jpeg", size_bytes: 123 }],
            resolved_address: "Kho Quận 7 — 12 Nguyễn Văn Linh",
            maps_url: mapsUrl,
          },
        ],
      }),
    });
    const view = render(<TaskManagementPanel />);
    fireEvent.click(screen.getByRole("button", { name: "Xem lịch sử" }));

    expect(await screen.findByText(/Kho Quận 7 — 12 Nguyễn Văn Linh/)).toBeInTheDocument();
    const link = screen.getByRole("link", { name: "Mở vị trí trên Google Maps" });
    expect(link).toHaveAttribute("href", mapsUrl);
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", "noopener noreferrer");
    expect(view.container.querySelector("iframe")).toBeNull();
    expect(view.container.querySelector("[data-exif-gps]")).toBeNull();
  });
});

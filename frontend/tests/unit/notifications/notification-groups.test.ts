import { describe, expect, it } from "vitest";

import { groupNotifications } from "@/features/notifications/model/notification-groups";
import type { NotificationItem } from "@/features/notifications/api/notification-api";

function item(publicId: string, createdAt: string): NotificationItem {
  return {
    public_id: publicId,
    created_at: createdAt,
    event_type: "TASK_ASSIGNED",
    title: publicId,
    read_at: null,
    is_unread: true,
  };
}

describe("notification date groups", () => {
  it("groups by local calendar day and sorts newest first", () => {
    const groups = groupNotifications(
      [
        item("old", "2026-08-18T10:00:00+07:00"),
        item("today-old", "2026-08-21T08:00:00+07:00"),
        item("yesterday", "2026-08-20T18:00:00+07:00"),
        item("today-new", "2026-08-21T12:00:00+07:00"),
      ],
      new Date("2026-08-21T14:00:00+07:00"),
    );

    expect(groups.map((group) => group.label)).toEqual(["Hôm nay", "Hôm qua", "Trước đó"]);
    expect(groups[0]?.items.map((value) => value.public_id)).toEqual(["today-new", "today-old"]);
  });

  it("omits empty groups", () => {
    expect(
      groupNotifications(
        [item("today", "2026-08-21T08:00:00+07:00")],
        new Date("2026-08-21T14:00:00+07:00"),
      ),
    ).toHaveLength(1);
  });
});

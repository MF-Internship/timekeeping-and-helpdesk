import { describe, expect, it } from "vitest";

import { replaceServerNotification } from "@/features/notifications/model/notification-state";

describe("notification state", () => {
  it("uses the server-confirmed item and derives a stable unread count", () => {
    const unread = {
      public_id: "9d872350-aa60-4aaa-8a4d-e3a26708a302",
      event_type: "TASK_ASSIGNED" as const,
      title: "Bạn có công việc mới",
      created_at: "2026-08-21T01:00:00Z",
      read_at: null,
      is_unread: true,
    };
    const next = replaceServerNotification(
      {
        items: [unread, { ...unread, public_id: "574f3e8b-d8c2-4d86-a3ba-8517807d7bee" }],
        unread_count: 2,
      },
      { ...unread, read_at: "2026-08-21T02:00:00Z", is_unread: false },
    );
    expect(next.unread_count).toBe(1);
    expect(next.items[0]?.read_at).toBe("2026-08-21T02:00:00Z");
  });
});

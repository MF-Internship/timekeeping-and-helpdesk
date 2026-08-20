import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

const markRead = vi.hoisted(() => vi.fn());
vi.mock("@/features/notifications/model/use-notifications", () => ({
  useNotifications: () => ({
    loadState: {
      kind: "ready",
      data: {
        unread_count: 1,
        items: [
          {
            public_id: "9d872350-aa60-4aaa-8a4d-e3a26708a302",
            event_type: "TASK_ASSIGNED",
            title: "Bạn có công việc mới",
            created_at: "2026-08-21T01:00:00Z",
            read_at: null,
            is_unread: true,
          },
        ],
      },
    },
    reads: {},
    refresh: vi.fn(),
    markRead,
  }),
}));
vi.mock("@/features/identity/model/AuthProvider", () => ({
  useAuth: () => ({ state: { kind: "authenticated", account: { id: 1 } } }),
}));

import { NotificationInbox } from "@/features/notifications/ui/NotificationInbox";

describe("notification inbox", () => {
  it("shows server unread state and never marks read when opening", () => {
    render(<NotificationInbox />);
    expect(screen.getByText("1 chưa đọc")).toBeInTheDocument();
    const open = screen.getByRole("link", { name: "Mở đích đến an toàn" });
    open.addEventListener("click", (event) => event.preventDefault());
    fireEvent.click(open);
    expect(markRead).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Đánh dấu đã đọc" }));
    expect(markRead).toHaveBeenCalledWith("9d872350-aa60-4aaa-8a4d-e3a26708a302");
  });
});

import type { NotificationInbox, NotificationItem } from "../api/notification-api";

export type NotificationLoadState =
  | { kind: "loading" }
  | { kind: "failed"; error: unknown }
  | { kind: "ready"; data: NotificationInbox; refreshError?: unknown };

export type NotificationReadState =
  | { kind: "idle" }
  | { kind: "submitting" }
  | { kind: "failed"; error: unknown };

export function replaceServerNotification(
  inbox: NotificationInbox,
  serverItem: NotificationItem,
): NotificationInbox {
  const items = inbox.items.map((item) =>
    item.public_id === serverItem.public_id ? serverItem : item,
  );
  return {
    items,
    unread_count: items.reduce((count, item) => count + (item.is_unread ? 1 : 0), 0),
  };
}

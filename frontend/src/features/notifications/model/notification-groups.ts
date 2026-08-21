import type { NotificationItem } from "../api/notification-api";
export type NotificationPeriod = "today" | "yesterday" | "earlier";
export type NotificationGroup = {
  period: NotificationPeriod;
  label: string;
  items: NotificationItem[];
};
const LABELS: Record<NotificationPeriod, string> = {
  today: "Hôm nay",
  yesterday: "Hôm qua",
  earlier: "Trước đó",
};
function dayKey(value: Date) {
  return `${value.getFullYear()}-${value.getMonth()}-${value.getDate()}`;
}
export function groupNotifications(
  items: readonly NotificationItem[],
  now = new Date(),
): NotificationGroup[] {
  const yesterday = new Date(now);
  yesterday.setDate(now.getDate() - 1);
  const buckets: Record<NotificationPeriod, NotificationItem[]> = {
    today: [],
    yesterday: [],
    earlier: [],
  };
  for (const item of [...items].sort(
    (a, b) => Date.parse(b.created_at) - Date.parse(a.created_at),
  )) {
    const created = new Date(item.created_at);
    const period =
      dayKey(created) === dayKey(now)
        ? "today"
        : dayKey(created) === dayKey(yesterday)
          ? "yesterday"
          : "earlier";
    buckets[period].push(item);
  }
  return (["today", "yesterday", "earlier"] as const)
    .filter((period) => buckets[period].length > 0)
    .map((period) => ({ period, label: LABELS[period], items: buckets[period] }));
}

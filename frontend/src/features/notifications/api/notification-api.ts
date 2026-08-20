import { apiClient } from "@/shared/api/client";
import { parseApiResultFailure } from "@/shared/errors/api-error";

export const NOTIFICATION_EVENT_TYPES = [
  "TASK_ASSIGNED",
  "TASK_UPCOMING",
  "TASK_OVERDUE",
  "ATTENDANCE_SESSION_OPEN_NEAR_SHIFT_END",
  "MULTI_ASSIGNEE_TASK_COMPLETED",
] as const;

export type NotificationEventType = (typeof NOTIFICATION_EVENT_TYPES)[number];
export type NotificationItem = {
  public_id: string;
  event_type: NotificationEventType;
  title: string;
  created_at: string;
  read_at: string | null;
  is_unread: boolean;
};
export type NotificationInbox = { items: NotificationItem[]; unread_count: number };
export type PushSubscriptionInput = { endpoint: string; p256dh: string; auth: string };
export type PushSubscriptionResult = { id: string; is_active: boolean; created_at: string };
export type NotificationTarget =
  | { destination: "TASK"; target_id: number }
  | { destination: "ATTENDANCE"; target_id: null };

type ApiResult<T> = { data?: T; error?: unknown; response: Response };
const client = apiClient;

async function unwrap<T>(result: ApiResult<T>): Promise<T> {
  if (result.data === undefined) throw await parseApiResultFailure(result);
  return result.data;
}

export async function listNotifications(): Promise<NotificationInbox> {
  return await unwrap(await client.GET("/api/v1/notifications/"));
}

export async function markNotificationRead(publicId: string): Promise<NotificationItem> {
  return await unwrap(
    await client.PATCH("/api/v1/notifications/{public_id}/read", {
      params: { path: { public_id: publicId } },
    }),
  );
}

export async function resolveNotificationTarget(publicId: string): Promise<NotificationTarget> {
  const target = await unwrap(
    await client.GET("/api/v1/notifications/{public_id}/target", {
      params: { path: { public_id: publicId } },
    }),
  );
  if (target.destination === "TASK" && typeof target.target_id === "number") {
    return { destination: "TASK", target_id: target.target_id };
  }
  if (target.destination === "ATTENDANCE" && target.target_id === null) {
    return { destination: "ATTENDANCE", target_id: null };
  }
  throw new Error("Unexpected notification target contract");
}

export async function registerPushSubscription(
  body: PushSubscriptionInput,
): Promise<PushSubscriptionResult> {
  return await unwrap(await client.POST("/api/v1/push-subscriptions/", { body }));
}

export async function revokePushSubscription(subscriptionId: string): Promise<void> {
  const result = await client.DELETE("/api/v1/push-subscriptions/{public_id}/", {
    params: { path: { public_id: subscriptionId } },
  });
  if (!result.response.ok) throw await parseApiResultFailure(result);
}

import { beforeEach, describe, expect, it, vi } from "vitest";

const client = vi.hoisted(() => ({ GET: vi.fn(), PATCH: vi.fn(), POST: vi.fn(), DELETE: vi.fn() }));
vi.mock("@/shared/api/client", () => ({ apiClient: client }));

import {
  listNotifications,
  markNotificationRead,
  registerPushSubscription,
  resolveNotificationTarget,
  revokePushSubscription,
} from "@/features/notifications/api/notification-api";

const ok = (data?: unknown, status = 200) => ({ data, response: new Response(null, { status }) });

beforeEach(() => vi.clearAllMocks());

describe("notification API boundary", () => {
  it("uses only self-scoped generated-client routes", async () => {
    client.GET.mockResolvedValueOnce(ok({ items: [], unread_count: 0 }));
    await expect(listNotifications()).resolves.toEqual({ items: [], unread_count: 0 });
    expect(client.GET).toHaveBeenCalledWith("/api/v1/notifications/");
  });

  it("sends no server-owned read fields and resolves before navigation", async () => {
    client.PATCH.mockResolvedValueOnce(ok({ public_id: "ref" }));
    client.GET.mockResolvedValueOnce(ok({ destination: "ATTENDANCE", target_id: null }));
    await markNotificationRead("ref");
    await resolveNotificationTarget("ref");
    expect(client.PATCH).toHaveBeenCalledWith(
      expect.stringContaining("/read"),
      expect.not.objectContaining({ body: expect.anything() }),
    );
    expect(client.GET).toHaveBeenLastCalledWith(
      expect.stringContaining("/target"),
      expect.anything(),
    );
  });

  it("registers opaque material and supports a 204 revoke", async () => {
    const body = { endpoint: "https://push.example/sub", p256dh: "key", auth: "auth" };
    client.POST.mockResolvedValueOnce(ok({ id: "opaque", is_active: true, created_at: "now" }));
    client.DELETE.mockResolvedValueOnce(ok(undefined, 204));
    await registerPushSubscription(body);
    await expect(revokePushSubscription("opaque")).resolves.toBeUndefined();
    expect(client.POST).toHaveBeenCalledWith("/api/v1/push-subscriptions/", { body });
  });
});

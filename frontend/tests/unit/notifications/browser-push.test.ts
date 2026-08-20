import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  readPushOwnerMarker,
  subscribeBrowserPush,
  unsubscribeBrowserPush,
  writePushOwnerMarker,
} from "@/features/notifications/adapters/browser-push";

const browserSubscription = {
  toJSON: () => ({
    endpoint: "https://push.example/sub",
    keys: { p256dh: "public", auth: "secret" },
  }),
  unsubscribe: vi.fn().mockResolvedValue(true),
};
const pushManager = { subscribe: vi.fn(), getSubscription: vi.fn() };
const registration = { pushManager };

beforeEach(() => {
  localStorage.clear();
  vi.clearAllMocks();
  Object.defineProperty(window, "PushManager", { configurable: true, value: class {} });
  Object.defineProperty(navigator, "serviceWorker", {
    configurable: true,
    value: {
      register: vi.fn().mockResolvedValue(registration),
      getRegistration: vi.fn().mockResolvedValue(registration),
    },
  });
});

describe("native browser push adapter", () => {
  it("subscribes only when called and projects the browser keys", async () => {
    pushManager.subscribe.mockResolvedValue(browserSubscription);
    const key = new Uint8Array(new ArrayBuffer(65));
    await expect(subscribeBrowserPush(key)).resolves.toMatchObject({
      input: { endpoint: "https://push.example/sub" },
    });
    expect(pushManager.subscribe).toHaveBeenCalledWith({
      userVisibleOnly: true,
      applicationServerKey: key,
    });
  });

  it("stores only account and opaque subscription identity and unsubscribes repeatedly", async () => {
    writePushOwnerMarker({ account_id: 7, subscription_id: "opaque" });
    expect(readPushOwnerMarker()).toEqual({ account_id: 7, subscription_id: "opaque" });
    expect(localStorage.getItem("web-push-owner")).not.toContain("endpoint");
    pushManager.getSubscription
      .mockResolvedValueOnce(browserSubscription)
      .mockResolvedValueOnce(null);
    await unsubscribeBrowserPush();
    await unsubscribeBrowserPush();
    expect(readPushOwnerMarker()).toBeUndefined();
  });
});

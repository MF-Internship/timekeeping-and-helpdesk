import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const browser = vi.hoisted(() => ({
  browserPushSupport: vi.fn(() => "supported"),
  clearPushOwnerMarker: vi.fn(),
  readPushOwnerMarker: vi.fn(),
  subscribeBrowserPush: vi.fn(),
  unsubscribeBrowserPush: vi.fn(),
  writePushOwnerMarker: vi.fn(),
}));
const api = vi.hoisted(() => ({
  registerPushSubscription: vi.fn(),
  revokePushSubscription: vi.fn(),
}));
vi.mock("@/features/notifications/adapters/browser-push", () => browser);
vi.mock("@/features/notifications/adapters/web-push-config", () => ({
  webPushConfiguration: () => ({ kind: "enabled", applicationServerKey: new Uint8Array(65) }),
}));
vi.mock("@/features/notifications/api/notification-api", () => api);
vi.mock("@/features/identity/model/AuthProvider", () => ({
  useAuth: () => ({ state: { kind: "authenticated", account: { id: 7 } } }),
}));

import { PushOptInControl } from "@/features/notifications/ui/PushOptInControl";

beforeEach(() => {
  vi.clearAllMocks();
  Object.defineProperty(globalThis, "Notification", {
    configurable: true,
    value: { permission: "default" },
  });
  browser.unsubscribeBrowserPush.mockResolvedValue(undefined);
});

describe("push opt-in control", () => {
  it("waits for an explicit gesture and reports enabled only after server storage", async () => {
    const subscription = { unsubscribe: vi.fn() };
    browser.subscribeBrowserPush.mockResolvedValue({
      browser: subscription,
      input: { endpoint: "https://push.example/sub", p256dh: "key", auth: "auth" },
    });
    api.registerPushSubscription.mockResolvedValue({ id: "opaque", is_active: true });
    render(<PushOptInControl />);
    const enable = await screen.findByRole("button", { name: "Bật Web Push" });
    expect(browser.subscribeBrowserPush).not.toHaveBeenCalled();
    fireEvent.click(enable);
    await screen.findByText("Web Push đang bật cho tài khoản này.");
    expect(browser.writePushOwnerMarker).toHaveBeenCalledWith({
      account_id: 7,
      subscription_id: "opaque",
    });
  });

  it("does not claim success when server storage fails", async () => {
    const unsubscribe = vi.fn().mockResolvedValue(true);
    browser.subscribeBrowserPush.mockResolvedValue({ browser: { unsubscribe }, input: {} });
    api.registerPushSubscription.mockRejectedValue(new Error("storage failed"));
    render(<PushOptInControl />);
    fireEvent.click(await screen.findByRole("button", { name: "Bật Web Push" }));
    await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("Không thể cập nhật"));
    expect(unsubscribe).toHaveBeenCalled();
    expect(browser.clearPushOwnerMarker).toHaveBeenCalled();
  });
});

import type { PushSubscriptionInput } from "../api/notification-api";

const MARKER_KEY = "web-push-owner";

export type PushOwnerMarker = { account_id: number; subscription_id: string };

export function browserPushSupport(): "supported" | "unsupported" {
  return typeof window !== "undefined" && "serviceWorker" in navigator && "PushManager" in window
    ? "supported"
    : "unsupported";
}

export function readPushOwnerMarker(): PushOwnerMarker | undefined {
  try {
    const value = localStorage.getItem(MARKER_KEY);
    if (!value) return undefined;
    const parsed = JSON.parse(value) as Record<string, unknown>;
    if (!Number.isSafeInteger(parsed.account_id) || typeof parsed.subscription_id !== "string") {
      clearPushOwnerMarker();
      return undefined;
    }
    return { account_id: Number(parsed.account_id), subscription_id: parsed.subscription_id };
  } catch {
    clearPushOwnerMarker();
    return undefined;
  }
}

export function writePushOwnerMarker(marker: PushOwnerMarker): void {
  localStorage.setItem(MARKER_KEY, JSON.stringify(marker));
}

export function clearPushOwnerMarker(): void {
  localStorage.removeItem(MARKER_KEY);
}

export async function subscribeBrowserPush(
  applicationServerKey: Uint8Array<ArrayBuffer>,
): Promise<{ browser: PushSubscription; input: PushSubscriptionInput }> {
  if (browserPushSupport() === "unsupported") throw new Error("PUSH_UNSUPPORTED");
  const registration = await navigator.serviceWorker.register("/notification-sw.js", {
    scope: "/",
  });
  const browser = await registration.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey,
  });
  const json = browser.toJSON();
  if (!json.endpoint || !json.keys?.p256dh || !json.keys.auth) {
    await browser.unsubscribe().catch(() => false);
    throw new Error("PUSH_SUBSCRIPTION_INVALID");
  }
  return {
    browser,
    input: { endpoint: json.endpoint, p256dh: json.keys.p256dh, auth: json.keys.auth },
  };
}

export async function unsubscribeBrowserPush(): Promise<void> {
  if (browserPushSupport() === "unsupported") {
    clearPushOwnerMarker();
    return;
  }
  try {
    const registration = await navigator.serviceWorker.getRegistration("/");
    const subscription = await registration?.pushManager.getSubscription();
    if (subscription) await subscription.unsubscribe();
  } finally {
    clearPushOwnerMarker();
  }
}

export async function clearPushForAccount(accountId?: number): Promise<void> {
  const marker = readPushOwnerMarker();
  if (marker && (accountId === undefined || marker.account_id === accountId)) {
    await unsubscribeBrowserPush();
  }
}

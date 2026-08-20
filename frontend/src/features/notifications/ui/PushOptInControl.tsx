"use client";

import { useEffect, useState } from "react";

import { useAuth } from "@/features/identity/model/AuthProvider";
import { Button } from "@/shared/ui/button";
import { Card } from "@/shared/ui/card";

import {
  browserPushSupport,
  clearPushOwnerMarker,
  readPushOwnerMarker,
  subscribeBrowserPush,
  unsubscribeBrowserPush,
  writePushOwnerMarker,
} from "../adapters/browser-push";
import { webPushConfiguration } from "../adapters/web-push-config";
import * as notificationApi from "../api/notification-api";
import styles from "./Notifications.module.css";

type State =
  | "checking"
  | "available"
  | "enabled"
  | "busy"
  | "denied"
  | "unsupported"
  | "disabled"
  | "error";

export function PushOptInControl() {
  const auth = useAuth();
  const accountId = auth.state.kind === "authenticated" ? auth.state.account.id : undefined;
  const configuration = webPushConfiguration();
  const [state, setState] = useState<State>(() => initialPushState(configuration.kind));
  usePushRestore(accountId, configuration.kind, setState);
  const actions = pushActions(accountId, configuration, setState);
  return (
    <Card aria-labelledby="push-heading" className={styles.pushCard}>
      <h3 id="push-heading">Web Push (tùy chọn)</h3>
      <p role="status" aria-live="polite">
        {pushStatus(state)}
      </p>
      {state === "available" || state === "error" ? (
        <Button onClick={() => void actions.enable()}>Bật Web Push</Button>
      ) : null}
      {state === "enabled" ? (
        <Button variant="destructive" onClick={() => void actions.disable()}>
          Hủy đăng ký Web Push
        </Button>
      ) : null}
      {state === "busy" ? (
        <Button loading disabled>
          Đang xử lý…
        </Button>
      ) : null}
    </Card>
  );
}

function pushActions(
  accountId: number | undefined,
  configuration: ReturnType<typeof webPushConfiguration>,
  setState: React.Dispatch<React.SetStateAction<State>>,
) {
  return {
    enable: () => enablePush(accountId, configuration, setState),
    disable: () => disablePush(accountId, setState),
  };
}

async function enablePush(
  accountId: number | undefined,
  configuration: ReturnType<typeof webPushConfiguration>,
  setState: React.Dispatch<React.SetStateAction<State>>,
) {
  if (accountId === undefined || configuration.kind !== "enabled") return;
  setState("busy");
  let browser: PushSubscription | undefined;
  try {
    const result = await subscribeBrowserPush(configuration.applicationServerKey);
    browser = result.browser;
    const stored = await notificationApi.registerPushSubscription(result.input);
    writePushOwnerMarker({ account_id: accountId, subscription_id: stored.id });
    setState("enabled");
  } catch {
    if (browser) await browser.unsubscribe().catch(() => false);
    clearPushOwnerMarker();
    setState(Notification.permission === "denied" ? "denied" : "error");
  }
}

async function disablePush(
  accountId: number | undefined,
  setState: React.Dispatch<React.SetStateAction<State>>,
) {
  if (accountId === undefined) return;
  setState("busy");
  const marker = readPushOwnerMarker();
  try {
    if (marker?.account_id === accountId) {
      await notificationApi.revokePushSubscription(marker.subscription_id);
    }
    await unsubscribeBrowserPush();
    setState("available");
  } catch {
    setState("error");
  }
}

function initialPushState(kind: ReturnType<typeof webPushConfiguration>["kind"]): State {
  if (kind === "disabled") return "disabled";
  if (kind === "invalid") return "error";
  if (browserPushSupport() === "unsupported") return "unsupported";
  if (Notification.permission === "denied") return "denied";
  return "checking";
}

function usePushRestore(
  accountId: number | undefined,
  configurationKind: ReturnType<typeof webPushConfiguration>["kind"],
  setState: React.Dispatch<React.SetStateAction<State>>,
) {
  useEffect(() => {
    let active = true;
    async function restoreEnabled() {
      const marker = readPushOwnerMarker();
      if (marker && marker.account_id !== accountId) {
        await unsubscribeBrowserPush().catch(clearPushOwnerMarker);
      }
      if (active) setState(marker?.account_id === accountId ? "enabled" : "available");
    }
    if (accountId !== undefined && configurationKind === "enabled") void restoreEnabled();
    return () => {
      active = false;
    };
  }, [accountId, configurationKind, setState]);
}

function pushStatus(state: State): string {
  const statuses: Record<State, string> = {
    checking: "Đang kiểm tra khả năng Web Push…",
    available: "Web Push đang tắt. Hộp thư trong ứng dụng vẫn hoạt động đầy đủ.",
    enabled: "Web Push đang bật cho tài khoản này.",
    busy: "Đang cập nhật đăng ký Web Push…",
    denied: "Trình duyệt đã từ chối quyền thông báo. Hộp thư vẫn hoạt động đầy đủ.",
    unsupported: "Trình duyệt này không hỗ trợ Web Push. Hộp thư vẫn hoạt động đầy đủ.",
    disabled: "Máy chủ chưa bật Web Push. Hộp thư vẫn hoạt động đầy đủ.",
    error: "Không thể cập nhật Web Push. Trạng thái chỉ được báo là bật sau khi máy chủ xác nhận.",
  };
  return statuses[state];
}

"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { useAuth } from "@/features/identity/model/AuthProvider";

import * as notificationApi from "../api/notification-api";
import {
  replaceServerNotification,
  type NotificationLoadState,
  type NotificationReadState,
} from "./notification-state";

export function useNotifications() {
  const auth = useAuth();
  const accountId = auth.state.kind === "authenticated" ? auth.state.account.id : undefined;
  const list = useNotificationList(accountId);
  const read = useReadNotifications(accountId, list.setLoadState);
  return { loadState: list.loadState, refresh: list.refresh, ...read };
}

function useNotificationList(accountId: number | undefined) {
  const [loadState, setLoadState] = useState<NotificationLoadState>({ kind: "loading" });
  const accountRef = useRef(accountId);
  const refresh = useCallback(async () => {
    if (accountId === undefined) return;
    const requestedAccount = accountId;
    try {
      const data = await notificationApi.listNotifications();
      if (accountRef.current === requestedAccount) setLoadState({ kind: "ready", data });
    } catch (error) {
      if (accountRef.current !== requestedAccount) return;
      setLoadState((current) =>
        current.kind === "ready" ? { ...current, refreshError: error } : { kind: "failed", error },
      );
    }
  }, [accountId]);
  useAccountNotifications(accountId, refresh, accountRef, setLoadState);
  useVisibleRefresh(accountId, refresh);
  return { loadState, setLoadState, refresh };
}

function useAccountNotifications(
  accountId: number | undefined,
  refresh: () => Promise<void>,
  accountRef: React.MutableRefObject<number | undefined>,
  setLoadState: React.Dispatch<React.SetStateAction<NotificationLoadState>>,
) {
  useEffect(() => {
    accountRef.current = accountId;
    setLoadState({ kind: "loading" });
    if (accountId !== undefined) queueMicrotask(() => void refresh());
  }, [accountId, accountRef, refresh, setLoadState]);
}

function useVisibleRefresh(accountId: number | undefined, refresh: () => Promise<void>) {
  useEffect(() => {
    if (accountId === undefined) return;
    const onVisibility = () => {
      if (document.visibilityState === "visible") void refresh();
    };
    document.addEventListener("visibilitychange", onVisibility);
    return () => document.removeEventListener("visibilitychange", onVisibility);
  }, [accountId, refresh]);
}

function useReadNotifications(
  accountId: number | undefined,
  setLoadState: React.Dispatch<React.SetStateAction<NotificationLoadState>>,
) {
  const [reads, setReads] = useState<Record<string, NotificationReadState>>({});
  const accountRef = useRef(accountId);
  useEffect(() => {
    accountRef.current = accountId;
    setReads({});
  }, [accountId]);
  const markRead = useCallback(
    async (publicId: string) => {
      if (accountId === undefined || reads[publicId]?.kind === "submitting") return;
      const requestedAccount = accountId;
      setReads((current) => ({ ...current, [publicId]: { kind: "submitting" } }));
      try {
        const item = await notificationApi.markNotificationRead(publicId);
        if (accountRef.current !== requestedAccount) return;
        setLoadState((current) => updateInbox(current, item));
        setReads((current) => ({ ...current, [publicId]: { kind: "idle" } }));
      } catch (error) {
        if (accountRef.current === requestedAccount) {
          setReads((current) => ({ ...current, [publicId]: { kind: "failed", error } }));
        }
      }
    },
    [accountId, reads, setLoadState],
  );
  return { reads, markRead };
}

function updateInbox(
  state: NotificationLoadState,
  item: notificationApi.NotificationItem,
): NotificationLoadState {
  return state.kind === "ready"
    ? { kind: "ready", data: replaceServerNotification(state.data, item) }
    : state;
}

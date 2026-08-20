"use client";

import Link from "next/link";

import { useNotifications } from "../model/use-notifications";
import styles from "./Notifications.module.css";

export function NotificationBadge() {
  const notifications = useNotifications();
  const count =
    notifications.loadState.kind === "ready"
      ? notifications.loadState.data.unread_count
      : undefined;
  return (
    <Link
      className={styles.headerLink}
      href="/notifications"
      aria-label={count === undefined ? "Thông báo" : `Thông báo, ${count} chưa đọc`}
    >
      Thông báo
      {count !== undefined && count > 0 ? (
        <span className={styles.headerCount}>{displayCount(count)}</span>
      ) : null}
    </Link>
  );
}

function displayCount(count: number): string | number {
  const maximumDisplayed = 99;
  return count > maximumDisplayed ? `${maximumDisplayed}+` : count;
}

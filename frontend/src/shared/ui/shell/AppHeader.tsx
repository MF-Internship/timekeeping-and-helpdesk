"use client";

import Link from "next/link";

import { useAuth } from "@/features/identity/model/AuthProvider";
import { MobiFoneLogo } from "@/shared/ui/brand";
import { NotificationBadge } from "@/features/notifications/ui/NotificationBadge";
import { ArrowLeft } from "lucide-react";
import { ThemeToggle } from "@/shared/ui/theme";
import { AccountMenu } from "./AccountMenu";

import styles from "./AppHeader.module.css";

export function AppHeader({
  title,
  backHref,
  backLabel = "Quay lại",
}: {
  title: string;
  backHref?: string;
  backLabel?: string;
}) {
  const auth = useAuth();
  const account = auth.state.kind === "authenticated" ? auth.state.account : undefined;
  return (
    <header className={styles.header}>
      <div className={styles.brand}>
        <MobiFoneLogo />
      </div>
      {backHref && (
        <Link href={backHref} aria-label={backLabel}>
          <ArrowLeft aria-hidden="true" />
        </Link>
      )}
      <div className={styles.context}>
        <span className={styles.eyebrow}>Trang hiện tại</span>
        <h1>{title}</h1>
      </div>
      {account ? (
        <div className={styles.account}>
          {account.capabilities?.includes("notification.view.self") ? <NotificationBadge /> : null}
          <ThemeToggle />
          <AccountMenu account={account} logout={auth.logout} />
        </div>
      ) : null}
    </header>
  );
}

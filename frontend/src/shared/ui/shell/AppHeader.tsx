"use client";

import Link from "next/link";

import { useAuth } from "@/features/identity/model/AuthProvider";
import { MobiFoneLogo } from "@/shared/ui/brand";
import { Button } from "@/shared/ui/button";

import styles from "./AppHeader.module.css";

function initials(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(-2)
    .map((part) => part[0]?.toUpperCase())
    .join("");
}

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
          ←
        </Link>
      )}
      <h1>{title}</h1>
      {account && (
        <div className={styles.account}>
          <Link
            href="/change-password"
            aria-label={`Tài khoản của ${account.full_name || account.username}`}
          >
            <span className={styles.avatar} aria-hidden="true">
              {initials(account.full_name || account.username)}
            </span>
          </Link>
          <span className={styles.name}>{account.full_name || account.username}</span>
          <Link className={styles.changePassword} href="/change-password">
            Đổi mật khẩu
          </Link>
          <Button variant="quiet" onClick={() => void auth.logout()} aria-label="Đăng xuất">
            Đăng xuất
          </Button>
        </div>
      )}
    </header>
  );
}

"use client";

import Link from "next/link";

import { useAuth } from "@/features/identity/model/AuthProvider";
import { MobiFoneLogo } from "@/shared/ui/brand";
import { Button } from "@/shared/ui/button";
import { Badge } from "@/shared/ui/badge";

import styles from "./AppHeader.module.css";

function initials(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(-2)
    .map((part) => part[0]?.toUpperCase())
    .join("");
}
const ROLE_LABELS: Record<string, string> = { MANAGER: "Quản lý", LEADER: "Trưởng nhóm", HELPDESK: "Nhân viên Helpdesk" };

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
      <div className={styles.context}><span className={styles.eyebrow}>Trang hiện tại</span><h1>{title}</h1></div>
      {account ? <AccountControls account={account} logout={auth.logout} /> : null}
    </header>
  );
}

function AccountControls({ account, logout }: {
  account: Extract<ReturnType<typeof useAuth>["state"], { kind: "authenticated" }>["account"];
  logout(): Promise<void>;
}) {
  return <div className={styles.account}>
          <Link
            href="/change-password"
            aria-label={`Tài khoản của ${account.full_name || account.username}`}
          >
            <span className={styles.avatar} aria-hidden="true">
              {initials(account.full_name || account.username)}
            </span>
          </Link>
          <span className={styles.name}>{account.full_name || account.username}</span>
          <Badge tone="neutral">{ROLE_LABELS[account.role] ?? account.role}</Badge>
          <Link className={styles.changePassword} href="/change-password">
            Đổi mật khẩu
          </Link>
          <Button variant="quiet" onClick={() => void logout()} aria-label="Đăng xuất">
            Đăng xuất
          </Button>
        </div>;
}

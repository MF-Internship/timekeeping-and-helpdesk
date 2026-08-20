"use client";

import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

import { useAuth } from "@/features/identity/model/AuthProvider";

import { AppHeader } from "./AppHeader";
import { employeeNavigation } from "./employee-navigation";
import { PrimaryNavigation } from "./PrimaryNavigation";
import styles from "./AppShell.module.css";

const PAGE_TITLES: Record<string, string> = { "/tasks": "Quản lý công việc", "/attendance": "Chấm công", "/users": "Quản lý người dùng", "/locations": "Địa điểm", "/holidays": "Ngày nghỉ", "/config": "Cấu hình vận hành", "/operations/job-health": "Sức khỏe đối soát", "/change-password": "Đổi mật khẩu" };
export function AppShell({ title, children }: { title?: string; children: ReactNode }) {
  const pathname = usePathname();
  const auth = useAuth();
  const items = employeeNavigation(auth.hasCapability);
  return (
    <div className={styles.shell}>
      <AppHeader title={title ?? PAGE_TITLES[pathname] ?? "Tổng quan"} />
      <div className={styles.body}>
        <PrimaryNavigation items={items} pathname={pathname} />
        <main className={styles.content}>{children}</main>
      </div>
    </div>
  );
}

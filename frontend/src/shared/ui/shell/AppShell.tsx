"use client";

import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

import { useAuth } from "@/features/identity/model/AuthProvider";

import { AppHeader } from "./AppHeader";
import { employeeNavigation } from "./employee-navigation";
import { PrimaryNavigation } from "./PrimaryNavigation";
import styles from "./AppShell.module.css";

export function AppShell({ title, children }: { title: string; children: ReactNode }) {
  const pathname = usePathname();
  const auth = useAuth();
  const items = employeeNavigation(auth.hasCapability);
  return (
    <div className={styles.shell}>
      <AppHeader title={title} />
      <div className={styles.body}>
        <PrimaryNavigation items={items} pathname={pathname} />
        <main className={styles.content}>{children}</main>
      </div>
    </div>
  );
}

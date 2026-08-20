"use client";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { AppShell } from "./AppShell";
export function ApplicationFrame({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  if (pathname === "/login") return <main className="auth-page">{children}</main>;
  return <AppShell>{children}</AppShell>;
}

"use client";

import { useEffect, type ReactNode } from "react";
import { useRouter } from "next/navigation";

import { useAuth } from "@/features/identity/model/AuthProvider";
import { UI_MESSAGES } from "@/shared/messages";

type IdentityRoute =
  | "home"
  | "account"
  | "login"
  | "change-password"
  | "users"
  | "locations"
  | "config"
  | "holidays"
  | "attendance"
  | "tasks"
  | "reports"
  | "notifications"
  | "job-health";

const REQUIRED_CAPABILITY = {
  users: "user.view",
  locations: "location.view",
  config: "config.view",
  holidays: "holiday.manage",
  attendance: "attendance.view.self",
  tasks: "task.view.self",
  reports: "report.view.self",
  notifications: "notification.view.self",
  "job-health": "operations.job_health.view",
} as const;

function destination(
  route: IdentityRoute,
  state: ReturnType<typeof useAuth>["state"],
): string | null {
  if (state.kind === "authenticated") return authenticatedDestination(route, state);
  const stateDestinations = {
    loading: () => null,
    inactive: () => "/login",
    forced_change: () => (route === "change-password" ? null : "/change-password"),
    anonymous: () => (route === "login" ? null : "/login"),
  } satisfies Record<typeof state.kind, () => string | null>;
  return stateDestinations[state.kind]();
}

function authenticatedDestination(
  route: IdentityRoute,
  state: Extract<ReturnType<typeof useAuth>["state"], { kind: "authenticated" }>,
): string | null {
  if (route === "login" || route === "change-password") return "/";
  if (route === "home" || route === "account") return null;
  return state.account.capabilities.includes(REQUIRED_CAPABILITY[route]) ? null : "/";
}

export function IdentityRouteBoundary({
  route,
  children,
}: {
  route: IdentityRoute;
  children: ReactNode;
}) {
  const auth = useAuth();
  const router = useRouter();
  const redirect = destination(route, auth.state);

  useEffect(() => {
    if (redirect) router.replace(redirect);
  }, [redirect, router]);

  if (auth.state.kind === "loading") return <p role="status">{UI_MESSAGES.loading}</p>;
  if (auth.state.kind === "inactive") return <p role="alert">{UI_MESSAGES.accountInactive}</p>;
  if (redirect) return null;
  return children;
}

"use client";

import { useAuth } from "@/features/identity/model/AuthProvider";
import { Button } from "@/shared/ui/button";

import type { TodayAttendance } from "../api/attendance-api";
import styles from "./AttendancePanel.module.css";

export function PrimaryAttendanceAction({
  today,
  busy,
  onPunch,
}: {
  today: TodayAttendance;
  busy: boolean;
  onPunch(): void;
}) {
  const auth = useAuth();
  const checkout = today.has_open_session;
  const capability = checkout ? "attendance.check_out.self" : "attendance.check_in.self";
  if (!auth.hasCapability(capability)) return null;
  const label = checkout ? "Check Out" : "Check In";
  return (
    <Button
      variant="primary"
      loading={busy}
      onClick={onPunch}
      className={styles.primaryAction}
      aria-label={busy ? `Đang ${label}` : label}
    >
      {busy ? `Đang ${label}…` : label}
    </Button>
  );
}

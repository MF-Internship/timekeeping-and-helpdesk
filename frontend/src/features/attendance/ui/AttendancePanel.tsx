"use client";

import { useGuidance } from "@/features/guidance/model/guidance-state";
import { GuidanceContent } from "@/features/guidance/ui/GuidancePanel";
import { ErrorState, LoadingState } from "@/shared/ui/async-state";
import { Card } from "@/shared/ui/card";

import { useAttendanceExperience } from "../model/use-attendance-experience";
import { AttendanceContextHeader } from "./AttendanceContextHeader";
import { AttendanceOutcomeCard } from "./AttendanceOutcomeCard";
import { LocationChoice } from "./LocationChoice";
import { PrimaryAttendanceAction } from "./PrimaryAttendanceAction";
import { TodayTimeline } from "./TodayTimeline";
import styles from "./AttendancePanel.module.css";

export function AttendancePanel() {
  const attendance = useAttendanceExperience();
  const guidance = useGuidance();
  if (!attendance.today) {
    return attendance.loadError ? (
      <ErrorState message={attendance.loadError} onRetry={() => void attendance.refresh()} />
    ) : (
      <LoadingState message="Đang tải…" />
    );
  }
  const today = attendance.today;
  const action = (
    <PrimaryAttendanceAction
      today={today}
      busy={attendance.busy}
      onPunch={() => void attendance.punch()}
    />
  );
  const outcome = (
    <>
      <AttendanceOutcomeCard outcome={attendance.outcome} onRetry={() => void attendance.punch()} />
      {attendance.candidates.length > 0 && (
        <LocationChoice
          candidates={attendance.candidates}
          disabled={attendance.busy}
          onSelect={(id) => void attendance.punch(id)}
        />
      )}
    </>
  );
  return (
    <div className={styles.page}>
      <GuidanceContent
        guidance={guidance}
        context={<AttendanceContextHeader today={today} />}
        primaryAction={action}
        outcome={outcome}
      />
      <Card aria-labelledby="today-history-title">
        <h2 id="today-history-title">Hôm nay</h2>
        <p>Tổng thời gian: {today.total_duration_minutes} phút</p>
        <TodayTimeline punches={today.punches} sessions={today.sessions} />
      </Card>
    </div>
  );
}

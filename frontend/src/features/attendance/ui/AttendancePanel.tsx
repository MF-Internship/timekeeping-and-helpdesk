"use client";

import { useCallback, useEffect, useState } from "react";

import * as attendanceApi from "@/features/attendance/api/attendance-api";
import {
  candidateFailure,
  freshCommand,
  type LocationCandidate,
} from "@/features/attendance/model/attendance-state";
import { useForegroundPosition } from "@/features/attendance/model/use-foreground-position";
import { LocationChoice } from "@/features/attendance/ui/LocationChoice";
import { TodayTimeline } from "@/features/attendance/ui/TodayTimeline";
import { useAuth } from "@/features/identity/model/AuthProvider";

export function AttendancePanel() {
  const gps = useForegroundPosition();
  const [today, setToday] = useState<attendanceApi.TodayAttendance>();
  const [error, setError] = useState<string>();
  const [busy, setBusy] = useState(false);
  const [candidates, setCandidates] = useState<LocationCandidate[]>([]);
  const refresh = useCallback(async () => setToday(await attendanceApi.getTodayAttendance()), []);

  useEffect(() => {
    let active = true;
    void attendanceApi.getTodayAttendance().then(
      (value) => active && setToday(value),
      () => active && setError("Không thể tải dữ liệu chấm công."),
    );
    return () => {
      active = false;
    };
  }, []);

  async function punch(selectedLocationId?: number) {
    setBusy(true);
    setError(undefined);
    try {
      const command = await freshCommand(gps.acquire, selectedLocationId);
      if (today?.has_open_session) await attendanceApi.checkOut(command);
      else await attendanceApi.checkIn(command);
      setCandidates([]);
      await refresh();
    } catch (failure) {
      const latest = candidateFailure(failure);
      if (latest) setCandidates(latest);
      else setError("Không thể hoàn tất chấm công. Vui lòng thử lại.");
    } finally {
      setBusy(false);
      gps.cancel();
    }
  }

  return (
    <AttendanceContent
      today={today}
      error={error}
      busy={busy || gps.loading}
      candidates={candidates}
      punch={punch}
    />
  );
}

function AttendanceContent({
  today,
  error,
  busy,
  candidates,
  punch,
}: {
  today?: attendanceApi.TodayAttendance;
  error?: string;
  busy: boolean;
  candidates: LocationCandidate[];
  punch(selectedLocationId?: number): Promise<void>;
}) {
  if (!today) {
    return (
      <section className="summary-card">
        <h2>Chấm công hôm nay</h2>
        {error ? <p role="alert">{error}</p> : <p>Đang tải…</p>}
      </section>
    );
  }
  return (
    <section className="summary-card">
      <h2>Chấm công hôm nay</h2>
      {error && <p role="alert">{error}</p>}
      <p>Tổng thời gian: {today.total_duration_minutes} phút</p>
      <PunchButton today={today} busy={busy} punch={punch} />
      {candidates.length > 0 && (
        <LocationChoice candidates={candidates} disabled={busy} onSelect={(id) => void punch(id)} />
      )}
      <TodayTimeline punches={today.punches} />
    </section>
  );
}

function PunchButton({
  today,
  busy,
  punch,
}: {
  today: attendanceApi.TodayAttendance;
  busy: boolean;
  punch(selectedLocationId?: number): Promise<void>;
}) {
  const auth = useAuth();
  const capability = today?.has_open_session
    ? "attendance.check_out.self"
    : "attendance.check_in.self";
  if (!auth.hasCapability(capability)) return null;
  return (
    <button type="button" disabled={busy} onClick={() => void punch()}>
      {today.has_open_session ? "Check Out" : "Check In"}
    </button>
  );
}

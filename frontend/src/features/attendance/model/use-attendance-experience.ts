"use client";

import { useCallback, useEffect, useState, type Dispatch, type SetStateAction } from "react";

import * as attendanceApi from "../api/attendance-api";
import { candidateFailure, freshCommand, type LocationCandidate } from "./attendance-state";
import { punchFailureMessage } from "./failure-messages";
import { useForegroundPosition } from "./use-foreground-position";

export type AttendanceOutcome =
  | { kind: "success"; action: "Check In" | "Check Out"; message: string }
  | { kind: "rejection"; message: string };

function useTodayAttendance() {
  const [today, setToday] = useState<attendanceApi.TodayAttendance>();
  const [loadError, setLoadError] = useState<string>();
  const refresh = useCallback(async () => setToday(await attendanceApi.getTodayAttendance()), []);
  useEffect(() => {
    let active = true;
    void attendanceApi.getTodayAttendance().then(
      (value) => active && setToday(value),
      () => active && setLoadError("Không thể tải dữ liệu chấm công."),
    );
    return () => {
      active = false;
    };
  }, []);
  return { today, loadError, refresh };
}

type PunchContext = {
  today: attendanceApi.TodayAttendance;
  acquire: ReturnType<typeof useForegroundPosition>["acquire"];
  cancel: () => void;
  refresh: () => Promise<void>;
  setBusy: Dispatch<SetStateAction<boolean>>;
  setOutcome: Dispatch<SetStateAction<AttendanceOutcome | undefined>>;
  setCandidates: Dispatch<SetStateAction<LocationCandidate[]>>;
};

async function performPunch(selectedLocationId: number | undefined, context: PunchContext) {
  const { today, acquire, cancel, refresh, setBusy, setOutcome, setCandidates } = context;
  const action = today.has_open_session ? "Check Out" : "Check In";
  setBusy(true);
  setOutcome(undefined);
  setCandidates([]);
  try {
    const command = await freshCommand(acquire, selectedLocationId);
    if (today.has_open_session) await attendanceApi.checkOut(command);
    else await attendanceApi.checkIn(command);
    await refresh();
    setOutcome({
      kind: "success",
      action,
      message: `${action} đã hoàn tất. Trạng thái ca làm việc đã được cập nhật.`,
    });
  } catch (failure) {
    const latest = candidateFailure(failure);
    if (latest) setCandidates(latest);
    const message = punchFailureMessage(failure);
    if (message) setOutcome({ kind: "rejection", message });
  } finally {
    setBusy(false);
    cancel();
  }
}

function usePunchExperience(
  today: attendanceApi.TodayAttendance | undefined,
  refresh: () => Promise<void>,
) {
  const gps = useForegroundPosition();
  const [outcome, setOutcome] = useState<AttendanceOutcome>();
  const [busy, setBusy] = useState(false);
  const [candidates, setCandidates] = useState<LocationCandidate[]>([]);
  const punch = useCallback(
    async (selectedLocationId?: number) => {
      if (!today) return;
      await performPunch(selectedLocationId, {
        today,
        acquire: gps.acquire,
        cancel: gps.cancel,
        refresh,
        setBusy,
        setOutcome,
        setCandidates,
      });
    },
    [gps, refresh, today],
  );
  return { outcome, busy: busy || gps.loading, candidates, punch };
}

export function useAttendanceExperience() {
  const todayState = useTodayAttendance();
  const punchState = usePunchExperience(todayState.today, todayState.refresh);
  return { ...todayState, ...punchState };
}

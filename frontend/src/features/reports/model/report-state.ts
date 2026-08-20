"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import {
  getAttendanceReport,
  getTaskReport,
  type AttendanceReport,
  type ReportFilters,
  type TaskReport,
} from "../api/report-api";

export type ReportState = {
  attendance?: AttendanceReport;
  tasks?: TaskReport;
  error?: unknown;
  loading: boolean;
  filters: ReportFilters;
  refresh: () => Promise<void>;
};

export function useReports(): ReportState {
  const filters = useMemo(() => defaultFilters(), []);
  const [attendance, setAttendance] = useState<AttendanceReport>();
  const [tasks, setTasks] = useState<TaskReport>();
  const [error, setError] = useState<unknown>();
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const [attendanceReport, taskReport] = await Promise.all([
        getAttendanceReport(filters),
        getTaskReport(filters),
      ]);
      setAttendance(attendanceReport);
      setTasks(taskReport);
      setError(undefined);
    } catch (failure) {
      setError(failure);
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    const timer = window.setTimeout(() => void refresh(), 0);
    return () => window.clearTimeout(timer);
  }, [refresh]);

  return { attendance, tasks, error, loading, filters, refresh };
}

function defaultFilters(): ReportFilters {
  const isoDateLength = 10;
  const today = new Date().toISOString().slice(0, isoDateLength);
  return { startDate: today, endDate: today };
}

"use client";

import { useReports } from "../model/report-state";
import { Button } from "@/shared/ui/button";

export function ReportsPanel() {
  const { attendance, tasks, error, loading, filters, refresh } = useReports();
  const hasData = Boolean(attendance || tasks);
  if (loading && !hasData) return <p role="status">Đang tải báo cáo…</p>;
  if (error && !hasData) return <p role="alert">Không thể tải báo cáo.</p>;
  return (
    <section aria-label="Báo cáo vận hành">
      <ReportControls loading={loading} filters={filters} refresh={refresh} />
      <RefreshError error={error} />
      {attendance ? <AttendanceSnapshot report={attendance} /> : null}
      {tasks ? <TaskSnapshot report={tasks} /> : null}
      <ExportLinks startDate={filters.startDate} endDate={filters.endDate} />
    </section>
  );
}

function ReportControls({
  loading,
  filters,
  refresh,
}: Pick<ReturnType<typeof useReports>, "loading" | "filters" | "refresh">) {
  return (
    <div>
      <p>
        Khoảng ngày: {filters.startDate} đến {filters.endDate}
      </p>
      <Button type="button" disabled={loading} onClick={() => void refresh()}>
        {loading ? "Đang làm mới…" : "Làm mới"}
      </Button>
    </div>
  );
}

function RefreshError({ error }: { error?: unknown }) {
  if (!error) return null;
  return <p role="alert">Lần làm mới gần nhất thất bại; đang hiển thị dữ liệu cũ.</p>;
}

function AttendanceSnapshot({ report }: { report: NonNullable<ReturnType<typeof useReports>["attendance"]> }) {
  return (
    <section aria-label="Báo cáo chấm công">
      <p>Đang trong ca: {report.users_in_open_session}</p>
      <p>Chưa Check In hôm nay: {report.users_no_check_in_today}</p>
      <p>Đã Check Out hôm nay: {report.users_checked_out_today}</p>
      <p>Số lượt chấm công: {report.punch_count}</p>
      <p>Phút công hợp lệ: {report.total_valid_worked_minutes}</p>
      <p>Tỉ lệ thất bại: {report.failure_rate.rate_percent ?? "N/A"}</p>
      <p>Bị loại khỏi mẫu: {report.failure_rate.excluded_count}</p>
    </section>
  );
}

function TaskSnapshot({ report }: { report: NonNullable<ReturnType<typeof useReports>["tasks"]> }) {
  return (
    <section aria-label="Báo cáo công việc">
      <p>Tổng công việc: {report.total_tasks}</p>
      <p>TODO: {report.status_counts.TODO ?? 0}</p>
      <p>IN_PROGRESS: {report.status_counts.IN_PROGRESS ?? 0}</p>
      <p>BLOCKED: {report.status_counts.BLOCKED ?? 0}</p>
      <p>COMPLETED: {report.status_counts.COMPLETED ?? 0}</p>
      <p>Công việc được giao đã đóng: {report.assigned_task_closed_count}</p>
    </section>
  );
}

function exportHref(kind: "attendance" | "tasks", startDate: string, endDate: string): string {
  return `/api/v1/reports/${kind}/export/?start_date=${startDate}&end_date=${endDate}`;
}

function ExportLinks({ startDate, endDate }: { startDate: string; endDate: string }) {
  return (
    <nav aria-label="Xuất báo cáo">
      <a href={exportHref("attendance", startDate, endDate)}>Xuất bảng công</a>
      <a href={exportHref("tasks", startDate, endDate)}>Xuất công việc</a>
    </nav>
  );
}

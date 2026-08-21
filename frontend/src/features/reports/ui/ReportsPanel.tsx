"use client";
import { Download, RefreshCw } from "lucide-react";
import { useState, type MouseEvent } from "react";
import { useReports } from "../model/report-state";
import { chartData, taskStatusData } from "../model/report-charts";
import { downloadReport } from "../api/report-api";
import { Button } from "@/shared/ui/button";
import { Card } from "@/shared/ui/card";
import { ErrorState, SkeletonState } from "@/shared/ui/async-state";
import { SectionHeader } from "@/shared/ui/typography";
import { CategoryChart } from "./CategoryChart";
import { useAuth } from "@/features/identity/model/AuthProvider";
import styles from "./ReportsPanel.module.css";
export function ReportsPanel() {
  const auth = useAuth();
  const { attendance, tasks, error, loading, filters, refresh } = useReports();
  const hasData = Boolean(attendance || tasks);
  if (loading && !hasData) return <SkeletonState rows={4} />;
  if (error && !hasData)
    return <ErrorState message="Không thể tải báo cáo." onRetry={() => void refresh()} />;
  return (
    <LoadedReports
      state={{ attendance, tasks, error, loading, filters, refresh }}
      canExport={auth.hasCapability("report.export")}
    />
  );
}

function LoadedReports({
  state,
  canExport,
}: {
  state: ReturnType<typeof useReports>;
  canExport: boolean;
}) {
  const { attendance, tasks, error, loading, filters, refresh } = state;
  return (
    <section aria-label="Báo cáo vận hành" className={styles.panel}>
      <div className={styles.toolbar}>
        <div>
          <span>Khoảng báo cáo</span>
          <strong>
            {formatDate(filters.startDate)} - {formatDate(filters.endDate)}
          </strong>
        </div>
        <Button type="button" disabled={loading} onClick={() => void refresh()}>
          <RefreshCw size={17} />
          {loading ? "Đang làm mới…" : "Làm mới"}
        </Button>
      </div>
      {error ? <p role="alert">Lần làm mới gần nhất thất bại; đang hiển thị dữ liệu cũ.</p> : null}
      {attendance ? <AttendanceReport report={attendance} /> : null}
      {tasks ? <TaskReport report={tasks} /> : null}
      {canExport ? <ExportActions filters={filters} /> : null}
    </section>
  );
}
function AttendanceReport({
  report,
}: {
  report: NonNullable<ReturnType<typeof useReports>["attendance"]>;
}) {
  const attempts = chartData(report.attempt_counts);
  const anomalies = chartData(report.anomaly_counts);
  return (
    <section>
      <SectionHeader
        title="Chấm công"
        description="Tổng hợp đúng theo khoảng báo cáo và phạm vi tài khoản hiện tại."
      />
      <div className={styles.metrics}>
        <Metric label="Đang trong ca" value={report.users_in_open_session} />
        <Metric label="Chưa Check In hôm nay" value={report.users_no_check_in_today} />
        <Metric label="Đã Check Out hôm nay" value={report.users_checked_out_today} />
        <Metric label="Lượt chấm công" value={report.punch_count} />
        <Metric label="Phút công hợp lệ" value={report.total_valid_worked_minutes} />
        <Metric
          label="Tỉ lệ thất bại"
          value={
            report.failure_rate.rate_percent === null
              ? "N/A"
              : `${report.failure_rate.rate_percent}%`
          }
        />
      </div>
      <ul className={styles.legacySummary}>
        <li>Tỉ lệ thất bại: {report.failure_rate.rate_percent ?? "N/A"}</li>
        <li>Bị loại khỏi mẫu: {report.failure_rate.excluded_count}</li>
      </ul>
      <div className={styles.charts}>
        {attempts.length ? <CategoryChart title="Kết quả lượt thử" data={attempts} /> : null}
        {anomalies.length ? <CategoryChart title="Bất thường chấm công" data={anomalies} /> : null}
      </div>
    </section>
  );
}
function TaskReport({ report }: { report: NonNullable<ReturnType<typeof useReports>["tasks"]> }) {
  const status = taskStatusData(report.status_counts);
  const methods = chartData(report.completion_method_counts);
  const gps = chartData(report.gps_quality_counts);
  return (
    <section>
      <SectionHeader
        title="Công việc"
        description="Phân bố trạng thái và phương thức hoàn thành từ dữ liệu báo cáo thực tế."
      />
      <div className={styles.metrics}>
        <Metric label="Tổng công việc" value={report.total_tasks} />
        <Metric label="Việc được giao đã đóng" value={report.assigned_task_closed_count} />
        <Metric label="Đã hoàn thành" value={report.status_counts.COMPLETED ?? 0} />
      </div>
      <p className="sr-only">Tổng công việc: {report.total_tasks}</p>
      <div className={styles.charts}>
        <CategoryChart title="Phân bố trạng thái" data={status} />
        {methods.length ? <CategoryChart title="Phương thức hoàn thành" data={methods} /> : null}
        {gps.length ? <CategoryChart title="Chất lượng GPS minh chứng" data={gps} /> : null}
      </div>
    </section>
  );
}
function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <Card className={styles.metric}>
      <span>{label}</span>
      <strong>{value}</strong>
    </Card>
  );
}
function ExportActions({ filters }: { filters: ReturnType<typeof useReports>["filters"] }) {
  const [busy, setBusy] = useState<string>();
  async function handle(event: MouseEvent<HTMLAnchorElement>, kind: "attendance" | "tasks") {
    event.preventDefault();
    setBusy(kind);
    try {
      const blob = await downloadReport(kind, filters);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `${kind}-${filters.startDate}-${filters.endDate}.csv`;
      link.click();
      URL.revokeObjectURL(url);
    } finally {
      setBusy(undefined);
    }
  }
  return (
    <section>
      <SectionHeader
        title="Xuất dữ liệu"
        description="Tệp xuất giữ nguyên công thức và phạm vi quyền của báo cáo."
      />
      <nav className={styles.exports} aria-label="Xuất báo cáo">
        <a
          href={exportHref("attendance", filters)}
          onClick={(event) => void handle(event, "attendance")}
          aria-busy={busy === "attendance"}
        >
          <Download />
          Xuất bảng công
        </a>
        <a
          href={exportHref("tasks", filters)}
          onClick={(event) => void handle(event, "tasks")}
          aria-busy={busy === "tasks"}
        >
          <Download />
          Xuất công việc
        </a>
      </nav>
    </section>
  );
}
function exportHref(
  kind: "attendance" | "tasks",
  filters: ReturnType<typeof useReports>["filters"],
) {
  return `/api/v1/reports/${kind}/export/?start_date=${filters.startDate}&end_date=${filters.endDate}${filters.userId === undefined ? "" : `&user_id=${filters.userId}`}`;
}
function formatDate(value: string) {
  return new Intl.DateTimeFormat("vi-VN").format(new Date(`${value}T00:00:00`));
}

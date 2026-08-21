"use client";
import { useCallback } from "react";
import Link from "next/link";
import { Bell, BriefcaseBusiness, ChartNoAxesCombined, Clock3, Wrench } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { useAuth } from "@/features/identity/model/AuthProvider";
import { getTodayAttendance } from "@/features/attendance/api/attendance-api";
import { listTasks, type GroupedTaskList } from "@/features/tasks/api/task-api";
import { listNotifications } from "@/features/notifications/api/notification-api";
import { getAttendanceReport, getTaskReport } from "@/features/reports/api/report-api";
import { getJobHealth } from "@/features/operations/api/job-health-api";
import { formatMinutes } from "@/shared/formatters/duration";
import { Card } from "@/shared/ui/card";
import { ErrorState, SkeletonState } from "@/shared/ui/async-state";
import { PageHeader, SectionHeader } from "@/shared/ui/typography";
import { useHomeResource } from "../model/use-home-dashboard";
import styles from "./HomeDashboard.module.css";
const today = () => new Date().toISOString().slice(0, 10);
export function HomeDashboard() {
  const { can, attendance, tasks, notifications, reports, health } = useDashboardResources();
  return (
    <section>
      <PageHeader
        title="Hôm nay"
        description="Những việc cần chú ý và lối tắt phù hợp với quyền hiện tại của bạn."
      />
      <div className={styles.metrics}>
        {attendance.data ? (
          <Metric
            icon={Clock3}
            label="Chấm công"
            value={attendance.data.has_open_session ? "Đang trong ca" : "Chưa trong ca"}
            href="/attendance"
            detail={`${formatMinutes(attendance.data.total_duration_minutes)} phút hợp lệ`}
          />
        ) : null}
        {tasks.data ? (
          <Metric
            icon={BriefcaseBusiness}
            label="Công việc quá hạn"
            value={String(tasks.data.overdue.length)}
            href="/tasks"
            detail={`${tasks.data.today.length} việc hôm nay`}
          />
        ) : null}
        {notifications.data ? (
          <Metric
            icon={Bell}
            label="Thông báo chưa đọc"
            value={String(notifications.data.unread_count)}
            href="/notifications"
            detail={`${notifications.data.items.length} thông báo gần đây`}
          />
        ) : null}
        {reports.data ? (
          <Metric
            icon={ChartNoAxesCombined}
            label="Công việc đang mở"
            value={String(openTasks(reports.data.tasks.status_counts))}
            href="/reports"
            detail={`${reports.data.attendance.users_in_open_session} nhân sự đang trong ca`}
          />
        ) : null}
        {health.data ? (
          <Metric
            icon={Wrench}
            label="Trạng thái vận hành"
            value={health.data.state}
            href="/operations/job-health"
            detail={`${health.data.overdue_open_session_count} phiên mở quá hạn`}
          />
        ) : null}
      </div>
      <ResourceErrors resources={[attendance, tasks, notifications, reports, health]} />
      <QuickLinks can={can} />
      <TaskPreview data={tasks.data} />
    </section>
  );
}

function useDashboardResources() {
  const auth = useAuth();
  const can = auth.hasCapability;
  const attendance = useHomeResource(
    can("attendance.view.self"),
    useCallback(() => getTodayAttendance(), []),
  );
  const tasks = useHomeResource(
    can("task.view.self"),
    useCallback(() => listTasks(), []),
  );
  const notifications = useHomeResource(
    can("notification.view.self"),
    useCallback(() => listNotifications(), []),
  );
  const reports = useHomeResource(
    can("report.view.self"),
    useCallback(async () => {
      const filters = { startDate: today(), endDate: today() };
      const [attendanceReport, taskReport] = await Promise.all([
        getAttendanceReport(filters),
        getTaskReport(filters),
      ]);
      return { attendance: attendanceReport, tasks: taskReport };
    }, []),
  );
  const health = useHomeResource(
    can("operations.job_health.view"),
    useCallback(() => getJobHealth(), []),
  );
  return { can, attendance, tasks, notifications, reports, health };
}
function openTasks(counts: Record<string, number>) {
  return (counts.TODO ?? 0) + (counts.IN_PROGRESS ?? 0) + (counts.BLOCKED ?? 0);
}
function Metric({
  icon: Icon,
  label,
  value,
  detail,
  href,
}: {
  icon: typeof Clock3;
  label: string;
  value: string;
  detail: string;
  href: string;
}) {
  return (
    <Card className={styles.metric}>
      <div className={styles.metricIcon}>
        <Icon aria-hidden="true" />
      </div>
      <div>
        <p>{label}</p>
        <strong>{value}</strong>
        <span>{detail}</span>
      </div>
      <Link href={href} aria-label={`Mở ${label}`}>
        Xem
      </Link>
    </Card>
  );
}
function ResourceErrors({
  resources,
}: {
  resources: readonly {
    loading: boolean;
    data?: unknown;
    error?: unknown;
    refresh(): Promise<void>;
  }[];
}) {
  const loading = resources.some((resource) => resource.loading && !resource.data);
  const failed = resources.find((resource) => resource.error && !resource.data);
  if (loading) return <SkeletonState rows={2} />;
  if (failed)
    return (
      <ErrorState
        message="Một phần tổng quan chưa tải được."
        onRetry={() => void failed.refresh()}
      />
    );
  return null;
}
function QuickLinks({ can }: { can: (capability: string) => boolean }) {
  const links: { href: string; label: string; capability: string; icon: LucideIcon }[] = [
    { href: "/tasks", label: "Công việc", capability: "task.view.self", icon: BriefcaseBusiness },
    { href: "/attendance", label: "Chấm công", capability: "attendance.view.self", icon: Clock3 },
    {
      href: "/notifications",
      label: "Thông báo",
      capability: "notification.view.self",
      icon: Bell,
    },
    {
      href: "/reports",
      label: "Báo cáo",
      capability: "report.view.self",
      icon: ChartNoAxesCombined,
    },
  ];
  const visible = links.filter((link) => can(link.capability));
  if (!visible.length) return null;
  return (
    <section className={styles.section}>
      <SectionHeader title="Truy cập nhanh" />
      <nav className={styles.quick} aria-label="Truy cập nhanh">
        {visible.map((link) => {
          const Icon = link.icon;
          return (
            <Link key={link.href} href={link.href}>
              <Icon aria-hidden="true" />
              {link.label}
            </Link>
          );
        })}
      </nav>
    </section>
  );
}
function TaskPreview({ data }: { data?: GroupedTaskList }) {
  if (!data) return null;
  const items = [...data.overdue, ...data.today].slice(0, 4);
  if (!items.length) return null;
  return (
    <section className={styles.section}>
      <SectionHeader title="Công việc cần chú ý" />
      <ul className={styles.taskList}>
        {items.map((task) => (
          <li key={task.id}>
            <Link href={`/tasks?focus=${task.id}`}>
              <strong>{task.title}</strong>
              <span>{task.status}</span>
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}

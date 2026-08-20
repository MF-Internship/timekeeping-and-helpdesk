export type EmployeeNavigationItem = {
  label: string;
  href: string;
  capability?: string;
};

const ITEMS: readonly EmployeeNavigationItem[] = [
  { label: "Thông báo", href: "/notifications", capability: "notification.view.self" },
  { label: "Công việc", href: "/tasks", capability: "task.view.self" },
  { label: "Chấm công", href: "/attendance", capability: "attendance.view.self" },
  { label: "Báo cáo", href: "/reports", capability: "report.view.self" },
  { label: "Người dùng", href: "/users", capability: "user.view" },
  { label: "Địa điểm", href: "/locations", capability: "location.view" },
  { label: "Ngày nghỉ", href: "/holidays", capability: "holiday.manage" },
  { label: "Cấu hình", href: "/config", capability: "config.view" },
  { label: "Vận hành", href: "/operations/job-health", capability: "operations.job_health.view" },
];

export function employeeNavigation(hasCapability: (capability: string) => boolean) {
  return ITEMS.filter((item) => !item.capability || hasCapability(item.capability));
}

import {
  Bell,
  BriefcaseBusiness,
  CalendarDays,
  ChartNoAxesCombined,
  Clock3,
  Home,
  MapPin,
  Settings,
  ShieldCheck,
  UserRound,
  UsersRound,
  Wrench,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
export type NavigationItem = {
  label: string;
  href: string;
  icon?: LucideIcon;
  capability?: string;
  group?: "primary" | "secondary" | "account";
  activePrefix?: boolean;
  implemented?: boolean;
};
const ITEMS: readonly NavigationItem[] = [
  { label: "Trang chủ", href: "/", icon: Home, group: "primary" },
  {
    label: "Công việc",
    href: "/tasks",
    icon: BriefcaseBusiness,
    capability: "task.view.self",
    group: "primary",
  },
  {
    label: "Chấm công",
    href: "/attendance",
    icon: Clock3,
    capability: "attendance.view.self",
    group: "primary",
  },
  {
    label: "Thông báo",
    href: "/notifications",
    icon: Bell,
    capability: "notification.view.self",
    group: "secondary",
    activePrefix: true,
  },
  {
    label: "Báo cáo",
    href: "/reports",
    icon: ChartNoAxesCombined,
    capability: "report.view.self",
    group: "secondary",
  },
  {
    label: "Người dùng",
    href: "/users",
    icon: UsersRound,
    capability: "user.view",
    group: "secondary",
  },
  {
    label: "Địa điểm",
    href: "/locations",
    icon: MapPin,
    capability: "location.view",
    group: "secondary",
  },
  {
    label: "Ngày nghỉ",
    href: "/holidays",
    icon: CalendarDays,
    capability: "holiday.manage",
    group: "secondary",
  },
  {
    label: "Cấu hình",
    href: "/config",
    icon: Settings,
    capability: "config.view",
    group: "secondary",
  },
  {
    label: "Vận hành",
    href: "/operations/job-health",
    icon: Wrench,
    capability: "operations.job_health.view",
    group: "secondary",
  },
  { label: "Tài khoản", href: "/account", icon: UserRound, group: "account" },
];
export function applicationNavigation(hasCapability: (capability: string) => boolean) {
  return ITEMS.filter((item) => !item.capability || hasCapability(item.capability));
}
export function isNavigationActive(item: NavigationItem, pathname: string) {
  return item.href === "/"
    ? pathname === "/"
    : item.activePrefix
      ? pathname === item.href || pathname.startsWith(`${item.href}/`)
      : pathname === item.href;
}
export const roleIcon = ShieldCheck;

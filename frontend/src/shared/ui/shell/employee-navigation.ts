export type EmployeeNavigationItem = {
  label: "Tasks" | "Attendance" | "Reports" | "Account";
  href: string;
  capability?: string;
  implemented: boolean;
};

const ITEMS: readonly EmployeeNavigationItem[] = [
  { label: "Tasks", href: "/tasks", capability: "task.view.self", implemented: false },
  {
    label: "Attendance",
    href: "/attendance",
    capability: "attendance.view.self",
    implemented: true,
  },
  { label: "Reports", href: "/reports", capability: "report.view.self", implemented: false },
  { label: "Account", href: "/account", implemented: false },
];

export function employeeNavigation(hasCapability: (capability: string) => boolean) {
  return ITEMS.filter(
    (item) => item.implemented && (!item.capability || hasCapability(item.capability)),
  );
}

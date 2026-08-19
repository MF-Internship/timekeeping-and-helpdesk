import type { ReactNode } from "react";

import { AppShell } from "@/shared/ui/shell/AppShell";

export default function EmployeeLayout({ children }: { children: ReactNode }) {
  return <AppShell title="Chấm công">{children}</AppShell>;
}

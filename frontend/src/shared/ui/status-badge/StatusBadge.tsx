import type { ReactNode } from "react";

import { Badge, type BadgeTone } from "@/shared/ui/badge";

export function StatusBadge({ children, tone }: { children: ReactNode; tone: BadgeTone }) {
  return <Badge tone={tone}>{children}</Badge>;
}

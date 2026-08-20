import type { HTMLAttributes } from "react";

import { cn } from "@/shared/lib/cn";

export function ActionGroup({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("flex flex-wrap items-center gap-3 pt-2", className)} {...props} />;
}

import type { ReactNode } from "react";

import { cn } from "@/shared/lib/cn";

export function Field(props: {
  label: string;
  htmlFor?: string;
  description?: ReactNode;
  error?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("grid gap-1.5", props.className)}>
      <label className="text-sm font-medium leading-none" htmlFor={props.htmlFor}>{props.label}</label>
      {props.children}
      {props.description ? <p className="text-sm text-muted-foreground">{props.description}</p> : null}
      {props.error ? <p className="text-sm text-destructive" role="alert">{props.error}</p> : null}
    </div>
  );
}

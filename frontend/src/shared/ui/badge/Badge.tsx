import type { ReactNode } from "react";

import styles from "./Badge.module.css";

export type BadgeTone = "neutral" | "ready" | "warning" | "critical";

export function Badge({
  tone = "neutral",
  icon,
  children,
}: {
  tone?: BadgeTone;
  icon?: ReactNode;
  children: ReactNode;
}) {
  return (
    <span className={`${styles.badge} ${styles[tone]}`}>
      {icon && <span aria-hidden="true">{icon}</span>}
      {children}
    </span>
  );
}

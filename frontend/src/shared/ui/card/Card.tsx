import type { HTMLAttributes, ReactNode } from "react";

import styles from "./Card.module.css";

export function Card({
  children,
  className = "",
  ...props
}: HTMLAttributes<HTMLElement> & { children: ReactNode }) {
  return (
    <section {...props} className={`${styles.card} ${className}`}>
      {children}
    </section>
  );
}

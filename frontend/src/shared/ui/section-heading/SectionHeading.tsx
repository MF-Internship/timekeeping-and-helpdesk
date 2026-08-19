import type { ReactNode } from "react";

import styles from "./SectionHeading.module.css";

export function SectionHeading({
  title,
  description,
  action,
  level = 2,
  id,
}: {
  title: string;
  description?: string;
  action?: ReactNode;
  level?: 2 | 3 | 4;
  id?: string;
}) {
  const Heading = `h${level}` as const;
  return (
    <header className={styles.header}>
      <div>
        <Heading id={id}>{title}</Heading>
        {description && <p>{description}</p>}
      </div>
      {action}
    </header>
  );
}

import type { HTMLAttributes, ReactNode } from "react";
import styles from "./Typography.module.css";
export function PageIntro({
  eyebrow,
  title,
  description,
}: {
  eyebrow?: string;
  title: string;
  description?: ReactNode;
}) {
  return (
    <header className={styles.intro}>
      {eyebrow ? <p className={styles.eyebrow}>{eyebrow}</p> : null}
      <h2 className={styles.title}>{title}</h2>
      {description ? <p className={styles.description}>{description}</p> : null}
    </header>
  );
}
export function MutedText(props: HTMLAttributes<HTMLParagraphElement>) {
  return <p {...props} className={`${styles.description} ${props.className ?? ""}`} />;
}

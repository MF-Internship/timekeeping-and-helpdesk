import { cva, type VariantProps } from "class-variance-authority";
import type { HTMLAttributes, ReactNode } from "react";
import { cn } from "@/shared/lib/cn";
import styles from "./Typography.module.css";
export const typography = cva("m-0", {
  variants: {
    variant: {
      pageTitle: styles.pageTitle,
      pageDescription: styles.description,
      sectionTitle: styles.sectionTitle,
      cardTitle: styles.cardTitle,
      body: styles.body,
      bodyMuted: styles.description,
      label: styles.label,
      caption: styles.caption,
      metric: styles.metric,
      warning: styles.warning,
    },
  },
  defaultVariants: { variant: "body" },
});
export function Text({
  variant,
  className,
  ...props
}: HTMLAttributes<HTMLParagraphElement> & VariantProps<typeof typography>) {
  return <p {...props} className={cn(typography({ variant }), className)} />;
}
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
      <h2 className={styles.pageTitle}>{title}</h2>
      {description ? <p className={styles.description}>{description}</p> : null}
    </header>
  );
}
export const PageHeader = PageIntro;
export function SectionHeader({ title, description }: { title: string; description?: ReactNode }) {
  return (
    <header className={styles.sectionHeader}>
      <h3 className={styles.sectionTitle}>{title}</h3>
      {description ? <p className={styles.description}>{description}</p> : null}
    </header>
  );
}
export function MutedText(props: HTMLAttributes<HTMLParagraphElement>) {
  return <Text {...props} variant="bodyMuted" />;
}

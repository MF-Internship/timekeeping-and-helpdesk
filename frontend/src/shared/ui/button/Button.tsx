import type { ButtonHTMLAttributes, ReactNode } from "react";
import { cva } from "class-variance-authority";
import { cn } from "@/shared/lib/cn";

export type ButtonVariant = "primary" | "secondary" | "quiet" | "destructive";

export type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
  loading?: boolean;
  children: ReactNode;
};
const buttonVariants = cva(
  "inline-flex min-h-[var(--touch-target)] items-center justify-center rounded-[var(--radius-md)] border border-transparent px-[var(--space-4)] py-[var(--space-3)] font-bold transition-colors disabled:pointer-events-none disabled:opacity-65",
  { variants: { variant: {
    primary: "bg-[var(--color-brand-primary)] text-[var(--color-brand-on-primary)] hover:bg-[var(--color-brand-primary-hover)]",
    secondary: "border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-text-primary)]",
    quiet: "bg-transparent text-[var(--color-brand-primary)]",
    destructive: "bg-[var(--color-critical)] text-[var(--color-brand-on-primary)]",
  } }, defaultVariants: { variant: "secondary" } },
);

export function Button({
  variant = "secondary",
  loading = false,
  disabled,
  children,
  ...props
}: ButtonProps) {
  return (
    <button
      {...props}
      className={cn(buttonVariants({ variant }), props.className)}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
    >
      {children}
    </button>
  );
}

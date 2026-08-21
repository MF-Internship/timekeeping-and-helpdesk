"use client";

import { Laptop, Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";

const OPTIONS = [
  { value: "light", label: "Sáng", icon: Sun },
  { value: "dark", label: "Tối", icon: Moon },
  { value: "system", label: "Hệ thống", icon: Laptop },
] as const;

export function ThemeToggle({ compact = true }: { compact?: boolean }) {
  const { theme = "system", setTheme } = useTheme();
  const current = OPTIONS.find((option) => option.value === theme) ?? OPTIONS[2];
  const Icon = current.icon;
  return (
    <label className="theme-toggle" suppressHydrationWarning>
      <span className="sr-only">Giao diện</span>
      <Icon aria-hidden="true" size={18} />
      <select
        aria-label="Giao diện"
        value={theme}
        onChange={(event) => setTheme(event.target.value)}
        suppressHydrationWarning
      >
        {OPTIONS.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
      {!compact ? <span>{current.label}</span> : null}
    </label>
  );
}

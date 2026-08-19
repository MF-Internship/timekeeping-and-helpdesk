import Link from "next/link";

import type { EmployeeNavigationItem } from "./employee-navigation";
import styles from "./PrimaryNavigation.module.css";

export function NavigationRail({
  items,
  pathname,
}: {
  items: readonly EmployeeNavigationItem[];
  pathname: string;
}) {
  return (
    <nav className={styles.rail} data-navigation="rail" aria-label="Điều hướng chính">
      <ul>
        {items.map((item) => (
          <li key={item.href}>
            <Link href={item.href} aria-current={pathname === item.href ? "page" : undefined}>
              {item.label}
            </Link>
          </li>
        ))}
      </ul>
    </nav>
  );
}

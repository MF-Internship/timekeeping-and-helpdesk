import Link from "next/link";

import type { NavigationItem } from "./navigation";
import { isNavigationActive } from "./navigation";
import styles from "./PrimaryNavigation.module.css";

export function NavigationRail({
  items,
  pathname,
}: {
  items: readonly NavigationItem[];
  pathname: string;
}) {
  return (
    <nav className={styles.rail} data-navigation="rail" aria-label="Điều hướng chính">
      <ul>
        {items.map((item) => (
          <li key={item.href}>
            <Link
              href={item.href}
              aria-current={isNavigationActive(item, pathname) ? "page" : undefined}
            >
              {item.icon ? <item.icon aria-hidden="true" /> : null}
              <span>{item.label}</span>
            </Link>
          </li>
        ))}
      </ul>
    </nav>
  );
}

import Link from "next/link";

import type { NavigationItem } from "./navigation";
import { isNavigationActive } from "./navigation";
import { MobileMoreMenu } from "./MobileMoreMenu";
import styles from "./PrimaryNavigation.module.css";

export function BottomNavigation({
  items,
  pathname,
}: {
  items: readonly NavigationItem[];
  pathname: string;
}) {
  return (
    <nav className={styles.bottom} data-navigation="bottom" aria-label="Điều hướng chính">
      <ul>
        {items
          .filter((item) => item.group === "primary" || item.group === undefined)
          .map((item) => (
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
        {items.some((item) => item.group && item.group !== "primary") ? (
          <li>
            <MobileMoreMenu
              items={items.filter((item) => item.group !== "primary")}
              pathname={pathname}
            />
          </li>
        ) : null}
      </ul>
    </nav>
  );
}

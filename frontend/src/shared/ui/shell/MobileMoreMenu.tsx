"use client";
import * as Dialog from "@radix-ui/react-dialog";
import { MoreHorizontal, X } from "lucide-react";
import Link from "next/link";
import type { NavigationItem } from "./navigation";
import { isNavigationActive } from "./navigation";
import styles from "./PrimaryNavigation.module.css";
export function MobileMoreMenu({
  items,
  pathname,
}: {
  items: readonly NavigationItem[];
  pathname: string;
}) {
  return (
    <Dialog.Root>
      <Dialog.Trigger asChild>
        <button className={styles.moreButton} aria-label="Mở thêm điều hướng">
          <MoreHorizontal aria-hidden="true" />
          <span>Khác</span>
        </button>
      </Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Overlay className={styles.sheetOverlay} />
        <Dialog.Content className={styles.sheet}>
          <div className={styles.sheetHeader}>
            <Dialog.Title>Điều hướng khác</Dialog.Title>
            <Dialog.Close aria-label="Đóng">
              <X />
            </Dialog.Close>
          </div>
          <nav aria-label="Điều hướng phụ">
            <ul className={styles.moreList}>
              {items.map((item) => {
                const Icon = item.icon;
                return (
                  <li key={item.href}>
                    <Dialog.Close asChild>
                      <Link
                        href={item.href}
                        aria-current={isNavigationActive(item, pathname) ? "page" : undefined}
                      >
                        {Icon ? <Icon aria-hidden="true" /> : null}
                        <span>{item.label}</span>
                      </Link>
                    </Dialog.Close>
                  </li>
                );
              })}
            </ul>
          </nav>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

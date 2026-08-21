"use client";

import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import { Check, KeyRound, LogOut, Palette, UserRound } from "lucide-react";
import Link from "next/link";
import { useTheme } from "next-themes";
import type { Account } from "@/features/identity/model/session-store";
import { roleLabel } from "@/shared/formatters/identity";
import styles from "./AppHeader.module.css";

function initials(name: string) {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(-2)
    .map((part) => part[0]?.toUpperCase())
    .join("");
}

type AccountMenuProps = {
  account: Account;
  logout(): Promise<void>;
  defaultOpen?: boolean;
};

export function AccountMenu({ account, logout, defaultOpen = false }: AccountMenuProps) {
  const name = account.full_name || account.username;
  const { theme = "system", setTheme } = useTheme();
  return (
    <DropdownMenu.Root defaultOpen={defaultOpen}>
      <DropdownMenu.Trigger asChild>
        <button className={styles.avatarButton} aria-label={`Mở menu tài khoản của ${name}`}>
          <span className={styles.avatar} aria-hidden="true">
            {initials(name)}
          </span>
        </button>
      </DropdownMenu.Trigger>
      <DropdownMenu.Portal>
        <DropdownMenu.Content className={styles.menu} align="end" sideOffset={8}>
          <div className={styles.menuIdentity}>
            <strong>{name}</strong>
            <span>{account.username}</span>
            <span>{roleLabel(account.role)}</span>
          </div>
          <DropdownMenu.Separator className={styles.menuSeparator} />
          <DropdownMenu.Item asChild>
            <Link className={styles.menuItem} href="/account">
              <UserRound size={17} />
              Tài khoản
            </Link>
          </DropdownMenu.Item>
          <DropdownMenu.Item asChild>
            <Link className={styles.menuItem} href="/change-password">
              <KeyRound size={17} />
              Đổi mật khẩu
            </Link>
          </DropdownMenu.Item>
          <DropdownMenu.Sub>
            <DropdownMenu.SubTrigger className={styles.menuItem}>
              <Palette size={17} />
              Giao diện
            </DropdownMenu.SubTrigger>
            <DropdownMenu.Portal>
              <DropdownMenu.SubContent className={styles.menu} sideOffset={6}>
                <DropdownMenu.RadioGroup value={theme} onValueChange={setTheme}>
                  {[
                    ["light", "Sáng"],
                    ["dark", "Tối"],
                    ["system", "Hệ thống"],
                  ].map(([value, label]) => (
                    <DropdownMenu.RadioItem className={styles.menuItem} value={value} key={value}>
                      <DropdownMenu.ItemIndicator className={styles.menuIndicator}>
                        <Check size={15} />
                      </DropdownMenu.ItemIndicator>
                      {label}
                    </DropdownMenu.RadioItem>
                  ))}
                </DropdownMenu.RadioGroup>
              </DropdownMenu.SubContent>
            </DropdownMenu.Portal>
          </DropdownMenu.Sub>
          <DropdownMenu.Separator className={styles.menuSeparator} />
          <DropdownMenu.Item className={styles.menuItem} onSelect={() => void logout()}>
            <LogOut size={17} />
            Đăng xuất
          </DropdownMenu.Item>
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  );
}

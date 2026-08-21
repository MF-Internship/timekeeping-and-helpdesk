import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { AccountMenu } from "@/shared/ui/shell/AccountMenu";

const account = {
  id: 7,
  username: "helpdesk",
  full_name: "Nguyễn An",
  role: "HELPDESK" as const,
  capabilities: [],
  phone: null,
  email: null,
  is_active: true,
  must_change_password: false,
};

describe("AccountMenu", () => {
  it("keeps account metadata and actions in the dropdown", () => {
    const logout = vi.fn().mockResolvedValue(undefined);
    render(<AccountMenu account={account} logout={logout} defaultOpen />);

    expect(screen.getByText("Nhân viên Helpdesk")).toBeInTheDocument();
    expect(screen.getByRole("menuitem", { name: "Tài khoản" })).toHaveAttribute("href", "/account");
    expect(screen.getByRole("menuitem", { name: "Đổi mật khẩu" })).toHaveAttribute(
      "href",
      "/change-password",
    );
    expect(screen.getByText("Giao diện")).toBeInTheDocument();
    expect(screen.getByRole("menuitemradio", { name: "Sáng" })).toBeInTheDocument();
    expect(screen.getByRole("menuitemradio", { name: "Tối" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("menuitem", { name: "Đăng xuất" }));
    expect(logout).toHaveBeenCalledOnce();
  });
});

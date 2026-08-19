import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { AppHeader } from "@/shared/ui/shell/AppHeader";

const logout = vi.fn();
vi.mock("@/features/identity/model/AuthProvider", () => ({
  useAuth: () => ({
    state: { kind: "authenticated", account: { full_name: "Nguyễn Văn An", username: "an" } },
    logout,
  }),
}));

describe("AppHeader", () => {
  it("shows title, approved brand, identity, initials, and existing account actions", () => {
    render(<AppHeader title="Chấm công" />);
    expect(screen.getByRole("heading", { name: "Chấm công", level: 1 })).toBeVisible();
    expect(screen.getByRole("img", { name: "MobiFone" })).toBeVisible();
    expect(screen.getByText("VA")).toHaveAttribute("aria-hidden", "true");
    expect(screen.getByRole("link", { name: "Tài khoản của Nguyễn Văn An" })).toHaveAttribute(
      "href",
      "/change-password",
    );
    expect(screen.getByRole("link", { name: "Đổi mật khẩu" })).toHaveAttribute(
      "href",
      "/change-password",
    );
    fireEvent.click(screen.getByRole("button", { name: "Đăng xuất" }));
    expect(logout).toHaveBeenCalledOnce();
  });

  it("supports an explicit labelled back action", () => {
    render(<AppHeader title="Chi tiết" backHref="/attendance" backLabel="Về Chấm công" />);
    expect(screen.getByRole("link", { name: "Về Chấm công" })).toHaveAttribute(
      "href",
      "/attendance",
    );
  });
});

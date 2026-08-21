import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { AppHeader } from "@/shared/ui/shell/AppHeader";

const logout = vi.fn();
vi.mock("@/features/identity/model/AuthProvider", () => ({
  useAuth: () => ({
    state: {
      kind: "authenticated",
      account: {
        id: 1,
        full_name: "Nguyễn Văn An",
        username: "an",
        role: "HELPDESK",
        capabilities: [],
        phone: null,
        email: null,
        is_active: true,
        must_change_password: false,
      },
    },
    logout,
  }),
}));

describe("AppHeader", () => {
  it("shows the current page, approved brand, theme control, and compact account trigger", () => {
    render(<AppHeader title="Chấm công" />);
    expect(screen.getByRole("heading", { name: "Chấm công", level: 1 })).toBeVisible();
    expect(screen.getByRole("img", { name: "MobiFone" })).toBeVisible();
    expect(screen.getByText("VA")).toHaveAttribute("aria-hidden", "true");
    expect(screen.getByRole("combobox", { name: "Giao diện" })).toBeVisible();
    expect(
      screen.getByRole("button", { name: "Mở menu tài khoản của Nguyễn Văn An" }),
    ).toHaveAttribute("aria-haspopup", "menu");
  });

  it("supports an explicit labelled back action", () => {
    render(<AppHeader title="Chi tiết" backHref="/attendance" backLabel="Về Chấm công" />);
    expect(screen.getByRole("link", { name: "Về Chấm công" })).toHaveAttribute(
      "href",
      "/attendance",
    );
  });
});

import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { AccountPanel } from "@/features/identity/ui/AccountPanel";

const logout = vi.fn();
vi.mock("@/features/identity/model/AuthProvider", () => ({
  useAuth: () => ({
    state: {
      kind: "authenticated",
      account: {
        id: 1,
        username: "an",
        full_name: "Nguyễn An",
        email: null,
        phone: null,
        role: "HELPDESK",
        is_active: true,
        must_change_password: false,
        capabilities: [],
      },
    },
    logout,
  }),
}));

describe("AccountPanel", () => {
  it("shows profile and supported preferences without session internals", () => {
    render(<AccountPanel />);
    expect(screen.getByText("Nguyễn An")).toBeInTheDocument();
    expect(screen.getByText("Nhân viên Helpdesk")).toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: "Giao diện" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Đổi mật khẩu" })).toHaveAttribute(
      "href",
      "/change-password",
    );
    expect(screen.queryByText(/JWT|access token|refresh token/i)).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Đăng xuất" }));
    expect(logout).toHaveBeenCalledOnce();
  });
});

import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { AppHeader } from "@/shared/ui/shell/AppHeader";

vi.mock("@/features/identity/model/AuthProvider", () => ({
  useAuth: () => ({
    state: { kind: "authenticated", account: {
      id: 7, username: "helpdesk", full_name: "Nguyễn An", role: "HELPDESK",
      capabilities: [], phone: null, email: null, is_active: true, must_change_password: false,
    } },
    logout: vi.fn(),
  }),
}));

describe("page header", () => {
  it("announces the current page, account and Vietnamese role label", () => {
    render(<AppHeader title="Công việc" />);
    expect(screen.getByRole("heading", { level: 1, name: "Công việc" })).toBeInTheDocument();
    expect(screen.getByText("Trang hiện tại")).toBeInTheDocument();
    expect(screen.getByText("Nhân viên Helpdesk")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Tài khoản của Nguyễn An" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Đăng xuất" })).toBeInTheDocument();
  });
});

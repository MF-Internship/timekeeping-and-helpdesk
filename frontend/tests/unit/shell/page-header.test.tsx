import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { AppHeader } from "@/shared/ui/shell/AppHeader";

vi.mock("@/features/identity/model/AuthProvider", () => ({
  useAuth: () => ({
    state: {
      kind: "authenticated",
      account: {
        id: 7,
        username: "helpdesk",
        full_name: "Nguyễn An",
        role: "HELPDESK",
        capabilities: [],
        phone: null,
        email: null,
        is_active: true,
        must_change_password: false,
      },
    },
    logout: vi.fn(),
  }),
}));

describe("page header", () => {
  it("announces the current page and exposes an accessible account menu trigger", () => {
    render(<AppHeader title="Công việc" />);
    expect(screen.getByRole("heading", { level: 1, name: "Công việc" })).toBeInTheDocument();
    expect(screen.getByText("Trang hiện tại")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Mở menu tài khoản của Nguyễn An" })).toHaveAttribute(
      "aria-haspopup",
      "menu",
    );
  });
});

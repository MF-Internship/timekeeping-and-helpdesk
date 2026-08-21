import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ThemeToggle } from "@/shared/ui/theme";

const theme = vi.hoisted(() => ({ current: "system", set: vi.fn() }));

vi.mock("next-themes", () => ({
  useTheme: () => ({ theme: theme.current, setTheme: theme.set }),
}));

describe("ThemeToggle", () => {
  it("offers Light, Dark and System and updates local theme preference", () => {
    render(<ThemeToggle compact={false} />);
    const select = screen.getByRole("combobox", { name: "Giao diện" });
    expect(screen.getAllByRole("option").map((option) => option.textContent)).toEqual([
      "Sáng",
      "Tối",
      "Hệ thống",
    ]);
    fireEvent.change(select, { target: { value: "dark" } });
    expect(theme.set).toHaveBeenCalledWith("dark");
  });
});

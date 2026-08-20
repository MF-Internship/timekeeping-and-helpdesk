import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { Button } from "@/shared/ui/button";

describe("Button", () => {
  it("keeps native button semantics and an accessible name", () => {
    const onClick = vi.fn();
    render(<Button onClick={onClick}>Tiếp tục</Button>);
    fireEvent.click(screen.getByRole("button", { name: "Tiếp tục" }));
    expect(onClick).toHaveBeenCalledOnce();
  });

  it("blocks activation while disabled or loading", () => {
    const onClick = vi.fn();
    const { rerender } = render(
      <Button disabled onClick={onClick}>
        Lưu
      </Button>,
    );
    expect(screen.getByRole("button", { name: "Lưu" })).toBeDisabled();
    rerender(
      <Button loading onClick={onClick}>
        Lưu
      </Button>,
    );
    expect(screen.getByRole("button", { name: "Lưu" })).toHaveAttribute("aria-busy", "true");
    fireEvent.click(screen.getByRole("button", { name: "Lưu" }));
    expect(onClick).not.toHaveBeenCalled();
  });

  it.each(["primary", "secondary", "quiet", "destructive"] as const)(
    "renders the %s variant",
    (variant) => {
      render(<Button variant={variant}>{variant}</Button>);
      expect(screen.getByRole("button", { name: variant })).toBeVisible();
    },
  );
});

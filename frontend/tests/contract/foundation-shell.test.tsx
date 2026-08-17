import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import Page from "@/app/page";

describe("foundation shell", () => {
  it("renders the shared-state showcase without a business workflow", () => {
    render(<Page />);
    expect(screen.getByRole("heading", { name: /nền tảng api/i })).toBeVisible();
    expect(screen.getAllByRole("status").length).toBeGreaterThanOrEqual(2);
    expect(screen.getAllByRole("alert").length).toBeGreaterThanOrEqual(3);
    expect(document.body.textContent).not.toMatch(/chấm công|giao việc|đăng nhập/i);
  });
});

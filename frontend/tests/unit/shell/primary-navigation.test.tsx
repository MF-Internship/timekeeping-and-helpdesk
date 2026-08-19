import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { PrimaryNavigation } from "@/shared/ui/shell/PrimaryNavigation";

const items = [
  {
    label: "Attendance" as const,
    href: "/attendance",
    capability: "attendance.view.self",
    implemented: true,
  },
];

describe("PrimaryNavigation", () => {
  it("uses one item set for phone bottom navigation and wider rail", () => {
    render(<PrimaryNavigation items={items} pathname="/attendance" />);
    const navigations = screen.getAllByRole("navigation", { name: "Điều hướng chính" });
    expect(navigations).toHaveLength(2);
    for (const navigation of navigations) {
      expect(within(navigation).getByRole("link", { name: "Attendance" })).toHaveAttribute(
        "aria-current",
        "page",
      );
    }
  });
});

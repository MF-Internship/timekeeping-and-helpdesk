import { describe, expect, it } from "vitest";

import { employeeNavigation } from "@/shared/ui/shell/employee-navigation";

describe("employee navigation registry", () => {
  it("shows only implemented destinations with an exact capability", () => {
    expect(
      employeeNavigation((capability) => capability === "attendance.view.self").map(
        (item) => item.label,
      ),
    ).toEqual(["Chấm công"]);
    expect(employeeNavigation(() => false)).toEqual([]);
    expect(
      employeeNavigation((capability) => capability === "task.view.self").map((item) => item.label),
    ).toEqual(["Công việc"]);
  });

  it("lists every implemented role destination without placeholder routes", () => {
    expect(employeeNavigation(() => true).map((item) => item.href)).toEqual([
      "/notifications",
      "/tasks",
      "/attendance",
      "/reports",
      "/users",
      "/locations",
      "/holidays",
      "/config",
      "/operations/job-health",
    ]);
  });
});

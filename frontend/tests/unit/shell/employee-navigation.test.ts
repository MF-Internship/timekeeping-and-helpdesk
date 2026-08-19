import { describe, expect, it } from "vitest";

import { employeeNavigation } from "@/shared/ui/shell/employee-navigation";

describe("employee navigation registry", () => {
  it("shows only implemented destinations with an exact capability", () => {
    expect(
      employeeNavigation((capability) => capability === "attendance.view.self").map(
        (item) => item.label,
      ),
    ).toEqual(["Attendance"]);
    expect(employeeNavigation(() => false)).toEqual([]);
  });

  it("does not invent Tasks, Reports, or Account routes", () => {
    expect(employeeNavigation(() => true).map((item) => item.href)).toEqual(["/attendance"]);
  });
});

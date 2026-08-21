import { describe, expect, it } from "vitest";

import { chartData, taskStatusData } from "@/features/reports/model/report-charts";

describe("report chart transforms", () => {
  it("uses the canonical task order and supplies truthful zero values", () => {
    expect(taskStatusData({ COMPLETED: 8, TODO: 5 })).toEqual([
      { key: "TODO", label: "Cần làm", value: 5 },
      { key: "IN_PROGRESS", label: "Đang thực hiện", value: 0 },
      { key: "BLOCKED", label: "Đang vướng", value: 0 },
      { key: "COMPLETED", label: "Đã hoàn thành", value: 8 },
    ]);
  });

  it("preserves real categories and sanitizes invalid aggregate values", () => {
    expect(chartData({ SUCCESS: 3, FAILED: Number.NaN, EXCLUDED: -2 })).toEqual([
      { key: "SUCCESS", label: "Success", value: 3 },
      { key: "FAILED", label: "Failed", value: 0 },
      { key: "EXCLUDED", label: "Excluded", value: 0 },
    ]);
  });
});

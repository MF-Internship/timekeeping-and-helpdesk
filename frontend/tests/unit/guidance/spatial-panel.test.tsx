import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { SpatialPanel } from "@/features/guidance/ui/SpatialPanel";

describe("SpatialPanel", () => {
  it("is closed by default, keeps a textual alternative, and mounts the SVG only after disclosure", async () => {
    await import("@/features/guidance/ui/SpatialDiagram");
    render(<SpatialPanel entries={[]} onFocus={vi.fn()} busy={false} />);
    const details = screen.getByText("Sơ đồ vị trí tương đối").closest("details");
    expect(details).not.toHaveAttribute("open");
    expect(details).toHaveTextContent(
      "Tên, địa chỉ, khoảng cách và trạng thái đầy đủ luôn có trong danh sách",
    );
    expect(screen.queryByRole("region", { name: "Sơ đồ tương đối" })).toBeNull();
    fireEvent.click(screen.getByText("Sơ đồ vị trí tương đối"));
    expect(await screen.findByRole("region", { name: "Sơ đồ tương đối" })).toHaveTextContent(
      "Chưa đủ dữ liệu vị trí",
    );
  });
});

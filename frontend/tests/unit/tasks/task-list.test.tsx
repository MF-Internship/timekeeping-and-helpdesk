import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { TaskManagementPanel } from "@/features/tasks/ui/TaskManagementPanel";

import { groupedFixture, managementFixture, taskFixture } from "./fixtures";

const controls = vi.hoisted(() => ({ management: {} as Record<string, unknown> }));
vi.mock("@/features/tasks/model/use-task-management", () => ({
  useTaskManagement: () => controls.management,
}));

afterEach(cleanup);

describe("Task grouped list", () => {
  it("renders status tabs and keeps server overdue membership authoritative", () => {
    const futureInServerOverdue = taskFixture({
      id: 1,
      title: "Server overdue",
      assigned_date: "2099-01-01",
    });
    const oldCompleted = taskFixture({
      id: 2,
      title: "Old completed",
      status: "COMPLETED",
      group: "COMPLETED",
      overdue_days: null,
    });
    controls.management = managementFixture({
      loadState: {
        kind: "ready",
        data: groupedFixture({ overdue: [futureInServerOverdue], completed: [oldCompleted] }),
      },
    });
    render(<TaskManagementPanel />);
    expect(screen.getByRole("tablist", { name: "Trạng thái công việc" })).toBeInTheDocument();
    fireEvent.mouseDown(screen.getByRole("tab", { name: /Quá hạn/ }), {
      button: 0,
      ctrlKey: false,
    });
    expect(within(screen.getByRole("tabpanel")).getByText("Server overdue")).toBeInTheDocument();
    fireEvent.mouseDown(screen.getByRole("tab", { name: /Đã xong/ }), {
      button: 0,
      ctrlKey: false,
    });
    expect(within(screen.getByRole("tabpanel")).getByText("Old completed")).toBeInTheDocument();
  });

  it("loads scoped detail history only after the user asks for it", async () => {
    const detail = vi.fn().mockResolvedValue({
      ...taskFixture(),
      updates: [
        {
          id: 5,
          actor: { id: 3, full_name: "An" },
          status: "IN_PROGRESS",
          recorded_at: "2026-08-20T08:00:00Z",
          note: null,
          block_reason: null,
          completion_method: null,
          completion_note: null,
        },
      ],
    });
    controls.management = managementFixture({
      loadState: { kind: "ready", data: groupedFixture({ today: [taskFixture()] }) },
      detail,
    });
    render(<TaskManagementPanel />);
    fireEvent.click(screen.getByRole("button", { name: "Xem lịch sử" }));
    expect(await screen.findByRole("region", { name: /Lịch sử/ })).toHaveTextContent(
      "Đang thực hiện",
    );
    expect(screen.getByRole("region", { name: /Lịch sử/ })).toHaveTextContent("An");
    expect(detail).toHaveBeenCalledWith(1);
  });

  it("renders server overdue days and the immutable original assigned date", () => {
    controls.management = managementFixture({
      loadState: {
        kind: "ready",
        data: groupedFixture({
          overdue: [taskFixture({ overdue_days: 4, assigned_date: "2026-08-16" })],
        }),
      },
    });
    render(<TaskManagementPanel />);
    expect(screen.getByText("Quá hạn 4 ngày")).toBeInTheDocument();
    expect(screen.getByText("16/08/2026")).toBeInTheDocument();
  });

  it("covers loading, empty, and retained-data refetch failure states", () => {
    controls.management = managementFixture({ loadState: { kind: "loading" } });
    const view = render(<TaskManagementPanel />);
    expect(screen.getByRole("status")).toHaveTextContent("Đang tải");
    controls.management = managementFixture({
      loadState: { kind: "ready", data: groupedFixture(), refreshError: new Error("offline") },
    });
    view.rerender(<TaskManagementPanel />);
    expect(screen.getByText("Không có công việc trong các nhóm hiện tại.")).toBeInTheDocument();
    expect(screen.getByText(/Không thể làm mới/)).toBeInTheDocument();
  });
});

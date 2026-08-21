import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { TaskFailureNotice } from "@/features/tasks/ui/TaskFailureNotice";
import { TaskForm } from "@/features/tasks/ui/TaskForm";

import { taskFixture } from "./fixtures";

describe("Task assignment presentation", () => {
  it("shows historical minimal identity outside the active-only addition picker", () => {
    const task = taskFixture({
      assignees: [
        { user: { id: 7, full_name: "Người đã nghỉ" }, assigned_at: "2026-08-01T00:00:00Z" },
      ],
    });
    render(
      <TaskForm
        mode="edit"
        task={task}
        editableAssignees
        users={[]}
        locations={[]}
        busy={false}
        onUpdate={vi.fn()}
      />,
    );
    expect(screen.getByText("Bỏ Người đã nghỉ")).toBeInTheDocument();
    expect(screen.getByText("Không có Helpdesk đang hoạt động.")).toBeInTheDocument();
    expect(JSON.stringify(task.assignees[0]?.user)).not.toContain("is_active");
  });

  it("omits assignment controls for Helpdesk content editing", () => {
    render(
      <TaskForm
        mode="edit"
        task={taskFixture()}
        users={[]}
        locations={[]}
        busy={false}
        onUpdate={vi.fn()}
      />,
    );
    expect(screen.queryByLabelText("Nhân viên Helpdesk đang hoạt động")).not.toBeInTheDocument();
  });

  it("submits the Manager full desired set from retained removals and active additions", async () => {
    const update = vi.fn().mockResolvedValue(undefined);
    render(
      <TaskForm
        mode="edit"
        task={taskFixture()}
        editableAssignees
        users={[{ id: 8, full_name: "Người mới" }] as never[]}
        locations={[]}
        busy={false}
        onUpdate={update}
      />,
    );
    fireEvent.click(screen.getByLabelText("Bỏ An"));
    fireEvent.click(screen.getByRole("checkbox", { name: /Người mới/ }));
    fireEvent.click(screen.getByRole("button", { name: "Lưu thay đổi" }));
    await vi.waitFor(() =>
      expect(update).toHaveBeenCalledWith(expect.objectContaining({ assignee_ids: [8] })),
    );
  });

  it("presents every ineligible assignee ID from the canonical failure", () => {
    render(
      <TaskFailureNotice
        error={{
          kind: "canonical",
          errorCode: "INACTIVE_ASSIGNEE",
          message: "Không thể giao",
          details: { assignee_ids: [3, 8, 12] },
          requestId: "123",
        }}
      />,
    );
    expect(
      screen.getByText("Một hoặc nhiều người được phân công không còn hợp lệ."),
    ).toBeInTheDocument();
    expect(screen.queryByText("3, 8, 12")).not.toBeInTheDocument();
  });
});

import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { TaskCard } from "@/features/tasks/ui/TaskCard";

import { managementFixture, taskFixture } from "./fixtures";

describe("Task capability-shaped controls", () => {
  it("shows Manager controls from exact capabilities", () => {
    const management = managementFixture({
      capabilities: {
        canCreateSelf: false,
        canAssign: true,
        canUpdateSelf: true,
        canUpdateAny: true,
        canDeleteSelf: false,
        canOverride: true,
      },
    });
    render(<TaskCard task={taskFixture()} management={management as never} onDetail={vi.fn()} />);
    expect(screen.getByRole("button", { name: "Sửa nội dung" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Hoàn thành" })).toBeInTheDocument();
  });

  it("shows Leader a read-only card rather than disabled mutations", () => {
    render(
      <TaskCard
        task={taskFixture()}
        management={managementFixture() as never}
        onDetail={vi.fn()}
      />,
    );
    expect(screen.getByText("Kiểm tra máy in")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /Sửa|Đổi trạng thái|Hoàn thành/ }),
    ).not.toBeInTheDocument();
  });

  it("freezes all mutation controls for COMPLETED", () => {
    const management = managementFixture({
      capabilities: {
        canCreateSelf: false,
        canAssign: true,
        canUpdateSelf: true,
        canUpdateAny: true,
        canDeleteSelf: false,
        canOverride: true,
      },
    });
    render(
      <TaskCard
        task={taskFixture({ status: "COMPLETED" })}
        management={management as never}
        onDetail={vi.fn()}
      />,
    );
    expect(screen.queryByRole("button", { name: "Hoàn thành" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Đổi trạng thái" })).not.toBeInTheDocument();
  });

  it("offers soft delete only for the current Helpdesk creator as sole assignee", () => {
    const remove = vi.fn().mockResolvedValue(undefined);
    const management = managementFixture({
      accountId: 3,
      remove,
      capabilities: {
        canCreateSelf: true,
        canAssign: false,
        canUpdateSelf: true,
        canUpdateAny: false,
        canDeleteSelf: true,
        canOverride: false,
        canCompleteField: true,
      },
    });
    render(
      <TaskCard
        task={taskFixture({ created_by: { id: 3, full_name: "An" } })}
        management={management as never}
        onDetail={vi.fn()}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Xóa task tự tạo" }));
    fireEvent.click(screen.getByRole("button", { name: "Xác nhận xóa" }));
    expect(remove).toHaveBeenCalledWith(1);
  });
});

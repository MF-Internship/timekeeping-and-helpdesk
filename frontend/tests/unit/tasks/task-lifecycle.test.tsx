import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ManagerOverrideForm } from "@/features/tasks/ui/ManagerOverrideForm";
import { TaskCard } from "@/features/tasks/ui/TaskCard";
import { TaskStatusForm } from "@/features/tasks/ui/TaskStatusForm";

import { managementFixture, taskFixture } from "./fixtures";

describe("Task lifecycle forms", () => {
  it("requires a reason when entering BLOCKED but permits same-state no-op", async () => {
    const submit = vi.fn().mockResolvedValue(undefined);
    const { rerender } = render(
      <TaskStatusForm task={taskFixture()} busy={false} onSubmit={submit} />,
    );
    fireEvent.change(screen.getByLabelText("Trạng thái"), { target: { value: "BLOCKED" } });
    fireEvent.click(screen.getByRole("button", { name: "Cập nhật trạng thái" }));
    expect(screen.getByText(/Cần nhập lý do/)).toBeInTheDocument();
    expect(submit).not.toHaveBeenCalled();
    rerender(
      <TaskStatusForm task={taskFixture({ status: "BLOCKED" })} busy={false} onSubmit={submit} />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Cập nhật trạng thái" }));
    await vi.waitFor(() =>
      expect(submit).toHaveBeenCalledWith(expect.objectContaining({ status: "BLOCKED" })),
    );
  });

  it("requires explicit confirmation and a nonblank Manager override note", async () => {
    const submit = vi.fn().mockResolvedValue(undefined);
    render(<ManagerOverrideForm taskTitle="Máy in" busy={false} onSubmit={submit} />);
    fireEvent.change(screen.getByLabelText("Ghi chú hoàn thành"), { target: { value: "Đã sửa" } });
    fireEvent.click(screen.getByRole("button", { name: "Hoàn thành" }));
    expect(submit).not.toHaveBeenCalled();
    fireEvent.click(screen.getByLabelText(/Xác nhận hoàn thành/));
    fireEvent.click(screen.getByRole("button", { name: "Hoàn thành" }));
    await vi.waitFor(() => expect(submit).toHaveBeenCalledWith("Đã sửa"));
  });

  it("renders allowed nonterminal actions and freezes completed cards", () => {
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
    const view = render(
      <TaskCard task={taskFixture()} management={management as never} onDetail={vi.fn()} />,
    );
    expect(screen.getByRole("button", { name: "Đổi trạng thái" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Hoàn thành" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Hoàn thành" }));
    expect(screen.getByRole("form", { name: /Hoàn thành/ })).toBeInTheDocument();
    view.rerender(
      <TaskCard
        task={taskFixture({ status: "COMPLETED" })}
        management={management as never}
        onDetail={vi.fn()}
      />,
    );
    expect(screen.queryByRole("button", { name: "Đổi trạng thái" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Hoàn thành" })).not.toBeInTheDocument();
  });
});

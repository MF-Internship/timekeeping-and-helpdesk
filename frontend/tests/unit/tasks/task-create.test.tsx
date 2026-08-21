import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { TaskForm } from "@/features/tasks/ui/TaskForm";

const users = [{ id: 2, full_name: "Helpdesk A", is_active: true }];
const locations = [{ id: 4, code: "HCM", name: "Quận 1", is_active: true }];

function fillRequired() {
  fireEvent.change(screen.getByLabelText("Tiêu đề"), { target: { value: "Sửa máy" } });
  fireEvent.change(screen.getByLabelText("Ngày giao"), { target: { value: "2026-08-20" } });
}

describe("Task create form", () => {
  it("accepts a free expected place, uses catalog suggestions, and resets after success", async () => {
    const create = vi.fn().mockResolvedValue(undefined);
    render(
      <TaskForm
        mode="assign-create"
        users={users as never[]}
        locations={locations as never[]}
        busy={false}
        onCreate={create}
      />,
    );
    fillRequired();
    fireEvent.click(screen.getByRole("checkbox", { name: /Helpdesk A/ }));
    fireEvent.change(screen.getByLabelText(/Địa điểm dự kiến/), {
      target: { value: "UBND phường 1" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Tạo công việc" }));
    await vi.waitFor(() =>
      expect(create).toHaveBeenCalledWith(
        expect.objectContaining({ assignee_ids: [2], expected_location: "UBND phường 1" }),
      ),
    );
    await vi.waitFor(() => expect(screen.getByLabelText("Tiêu đề")).toHaveValue(""));
    expect(screen.getByLabelText(/Địa điểm dự kiến/)).toHaveValue("");
  });

  it("keeps Helpdesk self-create free of assignee fields", () => {
    render(
      <TaskForm
        mode="self-create"
        users={users as never[]}
        locations={[]}
        busy={false}
        onCreate={vi.fn()}
      />,
    );
    expect(screen.queryByLabelText("Nhân viên Helpdesk đang hoạt động")).not.toBeInTheDocument();
  });

  it("suppresses duplicate submits and retains entered content after failure", async () => {
    let reject!: (reason: unknown) => void;
    const create = vi.fn(() => new Promise<void>((_, fail) => (reject = fail)));
    render(
      <TaskForm mode="self-create" users={[]} locations={[]} busy={false} onCreate={create} />,
    );
    fillRequired();
    const form = screen.getByRole("form", { name: "Tạo công việc" });
    fireEvent.submit(form);
    fireEvent.submit(form);
    expect(create).toHaveBeenCalledTimes(1);
    reject(new Error("network"));
    await vi.waitFor(() => expect(screen.getByLabelText("Tiêu đề")).toHaveValue("Sửa máy"));
  });
});

import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { UserDirectory } from "@/features/identity/ui/UserDirectory";

const controls = vi.hoisted(() => ({
  capabilities: new Set(["user.view", "user.manage", "user.assign_role"]),
  listUsers: vi.fn(),
  createUser: vi.fn(),
  updateUser: vi.fn(),
  changeUserRole: vi.fn(),
  changeUserStatus: vi.fn(),
  resetUserPassword: vi.fn(),
}));

vi.mock("@/features/identity/model/AuthProvider", () => ({
  useAuth: () => ({ hasCapability: (value: string) => controls.capabilities.has(value) }),
}));
vi.mock("@/features/identity/api/identity-api", () => ({
  listUsers: controls.listUsers,
  createUser: controls.createUser,
  updateUser: controls.updateUser,
  changeUserRole: controls.changeUserRole,
  changeUserStatus: controls.changeUserStatus,
  resetUserPassword: controls.resetUserPassword,
}));

const manager = {
  id: 1,
  username: "manager",
  full_name: "Manager",
  phone: null,
  email: null,
  role: "MANAGER",
  is_active: true,
  must_change_password: false,
};
const worker = { ...manager, id: 2, username: "worker", full_name: "Worker", role: "HELPDESK" };

function openUserActions(name = "Worker") {
  fireEvent.keyDown(screen.getByRole("button", { name: `Thao tác với ${name}` }), {
    key: "Enter",
  });
}

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
  controls.capabilities = new Set(["user.view", "user.manage", "user.assign_role"]);
});

describe("UserDirectory", () => {
  it("shows every target but never offers Manager mutation controls", async () => {
    controls.listUsers.mockResolvedValue({
      results: [manager, worker],
      next: null,
      previous: null,
    });
    render(<UserDirectory />);
    await screen.findByText("Manager", { selector: "strong" });
    expect(screen.getByText("Worker", { selector: "strong" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Thao tác với Manager" })).not.toBeInTheDocument();
    openUserActions();
    expect(screen.getByRole("menuitem", { name: "Sửa hồ sơ" })).toBeInTheDocument();
    expect(screen.getByRole("menuitem", { name: "Đổi vai trò" })).toBeInTheDocument();
    fireEvent.keyDown(screen.getByRole("menu"), { key: "Escape" });
  });

  it("sends combined filters and resets a new search to page one", async () => {
    controls.listUsers.mockResolvedValue({
      results: [],
      next: "/api/v1/users/?page=2",
      previous: null,
    });
    render(<UserDirectory />);
    await waitFor(() => expect(controls.listUsers).toHaveBeenCalledWith({ offset: 0, limit: 20 }));
    const nextButton = screen.getByRole("button", { name: "Trang sau" });
    await waitFor(() => expect(nextButton).toBeEnabled());
    fireEvent.click(nextButton);
    await waitFor(() =>
      expect(controls.listUsers).toHaveBeenLastCalledWith({ offset: 20, limit: 20 }),
    );
    fireEvent.change(screen.getByLabelText("Tìm kiếm"), { target: { value: "worker" } });
    fireEvent.change(screen.getAllByLabelText("Vai trò")[0], { target: { value: "HELPDESK" } });
    fireEvent.change(screen.getByLabelText("Trạng thái"), { target: { value: "false" } });
    fireEvent.click(screen.getByRole("button", { name: "Tìm" }));
    await waitFor(() =>
      expect(controls.listUsers).toHaveBeenLastCalledWith({
        q: "worker",
        role: "HELPDESK",
        is_active: false,
        offset: 0,
        limit: 20,
      }),
    );
  });

  it("shows the current page, total pages, and visible account range", async () => {
    controls.listUsers.mockResolvedValue({
      count: 45,
      results: [worker],
      next: "/api/v1/users/?offset=20",
      previous: null,
    });
    render(<UserDirectory />);
    expect(await screen.findByText("Trang 1", { exact: false })).toHaveTextContent("/ 3");
    expect(screen.getByText("Hiển thị 1–20 trong 45 tài khoản")).toBeInTheDocument();
  });

  it("uses distinct mutations and hands generated reset plaintext only to the dialog", async () => {
    controls.listUsers.mockResolvedValue({ results: [worker], next: null, previous: null });
    controls.changeUserStatus.mockResolvedValue({});
    controls.changeUserRole.mockResolvedValue({});
    controls.resetUserPassword.mockResolvedValue({ generated_password: "ResetOnly123!" });
    render(<UserDirectory />);
    await screen.findByText("Worker", { selector: "strong" });
    openUserActions();
    fireEvent.click(screen.getByRole("menuitem", { name: "Khóa" }));
    openUserActions();
    fireEvent.click(screen.getByRole("menuitem", { name: "Đổi vai trò" }));
    openUserActions();
    fireEvent.click(screen.getByRole("menuitem", { name: "Đặt lại mật khẩu" }));
    await waitFor(() => expect(controls.changeUserStatus).toHaveBeenCalledWith(2, false));
    expect(controls.changeUserRole).toHaveBeenCalledWith(2, "LEADER");
    expect(await screen.findByRole("dialog")).toHaveTextContent("ResetOnly123!");
  });

  it("renders a denied mutation without storing any generated plaintext", async () => {
    controls.listUsers.mockResolvedValue({ results: [worker], next: null, previous: null });
    controls.changeUserStatus.mockRejectedValue({
      kind: "canonical",
      errorCode: "PERMISSION_DENIED",
      message: "ignored server copy",
      details: {},
      requestId: "123e4567-e89b-42d3-a456-426614174000",
    });
    render(<UserDirectory />);
    await screen.findByText("Worker", { selector: "strong" });
    openUserActions();
    fireEvent.click(screen.getByRole("menuitem", { name: "Khóa" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Bạn không có quyền thực hiện thao tác này.",
    );
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Mã yêu cầu: 123e4567-e89b-42d3-a456-426614174000",
    );
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("edits profile contacts through the typed form and normalizes blanks to null", async () => {
    controls.listUsers.mockResolvedValue({ results: [worker], next: null, previous: null });
    controls.updateUser.mockResolvedValue({});
    render(<UserDirectory />);
    await screen.findByText("Worker", { selector: "strong" });
    openUserActions();
    fireEvent.click(screen.getByRole("menuitem", { name: "Sửa hồ sơ" }));
    const form = screen.getByRole("form", { name: "Sửa hồ sơ người dùng" });
    fireEvent.change(within(form).getByLabelText("Họ tên"), {
      target: { value: "Worker Updated" },
    });
    fireEvent.change(within(form).getByLabelText("Điện thoại"), {
      target: { value: "   " },
    });
    fireEvent.change(within(form).getByLabelText("Email"), {
      target: { value: "" },
    });
    fireEvent.submit(form);
    await waitFor(() =>
      expect(controls.updateUser).toHaveBeenCalledWith(2, {
        full_name: "Worker Updated",
        phone: null,
        email: null,
      }),
    );
  });

  it("cancels profile editing without issuing a mutation", async () => {
    controls.listUsers.mockResolvedValue({ results: [worker], next: null, previous: null });
    render(<UserDirectory />);
    await screen.findByText("Worker", { selector: "strong" });
    openUserActions();
    fireEvent.click(screen.getByRole("menuitem", { name: "Sửa hồ sơ" }));
    fireEvent.click(screen.getByRole("button", { name: "Hủy" }));
    expect(screen.queryByRole("form", { name: "Sửa hồ sơ người dùng" })).not.toBeInTheDocument();
    expect(controls.updateUser).not.toHaveBeenCalled();
  });

  it("blocks an invalid email before the profile API is called", async () => {
    controls.listUsers.mockResolvedValue({ results: [worker], next: null, previous: null });
    render(<UserDirectory />);
    await screen.findByText("Worker", { selector: "strong" });
    openUserActions();
    fireEvent.click(screen.getByRole("menuitem", { name: "Sửa hồ sơ" }));
    const form = screen.getByRole("form", { name: "Sửa hồ sơ người dùng" });
    fireEvent.change(within(form).getByLabelText("Email"), {
      target: { value: "not-an-email" },
    });
    fireEvent.click(within(form).getByRole("button", { name: "Lưu hồ sơ" }));
    expect(controls.updateUser).not.toHaveBeenCalled();
  });

  it("keeps the edit form open when the server protects the target", async () => {
    controls.listUsers.mockResolvedValue({ results: [worker], next: null, previous: null });
    controls.updateUser.mockRejectedValue({
      kind: "canonical",
      errorCode: "PERMISSION_DENIED",
      message: "ignored",
      details: {},
      requestId: "123e4567-e89b-42d3-a456-426614174002",
    });
    render(<UserDirectory />);
    await screen.findByText("Worker", { selector: "strong" });
    openUserActions();
    fireEvent.click(screen.getByRole("menuitem", { name: "Sửa hồ sơ" }));
    const form = screen.getByRole("form", { name: "Sửa hồ sơ người dùng" });
    fireEvent.submit(form);

    expect(await within(form).findByRole("alert")).toHaveTextContent(
      "Bạn không có quyền thực hiện thao tác này.",
    );
    expect(form).toBeInTheDocument();
  });
});

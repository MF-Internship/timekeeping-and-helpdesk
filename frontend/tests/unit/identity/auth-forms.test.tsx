import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { setSessionState } from "@/features/identity/model/session-store";
import { ChangePasswordForm } from "@/features/identity/ui/ChangePasswordForm";
import { LoginForm } from "@/features/identity/ui/LoginForm";

const controls = vi.hoisted(() => ({
  login: vi.fn(),
  changePassword: vi.fn(),
  replace: vi.fn(),
}));
vi.mock("next/navigation", () => ({ useRouter: () => ({ replace: controls.replace }) }));
vi.mock("@/features/identity/model/AuthProvider", () => ({
  useAuth: () => ({
    state: { kind: "anonymous" },
    login: controls.login,
    changePassword: controls.changePassword,
  }),
}));

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("identity forms", () => {
  it("routes a forced-login result only to password change", async () => {
    controls.login.mockImplementation(async () => setSessionState({ kind: "forced_change" }));
    render(<LoginForm />);
    fireEvent.change(screen.getByLabelText("Tên đăng nhập"), { target: { value: "worker" } });
    fireEvent.change(screen.getByLabelText("Mật khẩu"), { target: { value: "Password123!" } });
    fireEvent.click(screen.getByRole("button", { name: "Đăng nhập" }));
    await waitFor(() => expect(controls.replace).toHaveBeenCalledWith("/change-password"));
  });

  it("submits current and compliant replacement passwords", async () => {
    controls.changePassword.mockResolvedValue(undefined);
    render(<ChangePasswordForm />);
    fireEvent.change(screen.getByLabelText("Mật khẩu hiện tại"), {
      target: { value: "OldPassword123!" },
    });
    fireEvent.change(screen.getByLabelText("Mật khẩu mới"), {
      target: { value: "NewPassword456!" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Đổi mật khẩu" }));
    await waitFor(() =>
      expect(controls.changePassword).toHaveBeenCalledWith("OldPassword123!", "NewPassword456!"),
    );
    expect(controls.replace).toHaveBeenCalledWith("/");
  });

  it("renders canonical login semantics and request correlation", async () => {
    controls.login.mockRejectedValue({
      kind: "canonical",
      errorCode: "INVALID_CREDENTIALS",
      message: "server copy is not presentation text",
      details: {},
      requestId: "123e4567-e89b-42d3-a456-426614174000",
    });
    render(<LoginForm />);
    fireEvent.change(screen.getByLabelText("Tên đăng nhập"), { target: { value: "worker" } });
    fireEvent.change(screen.getByLabelText("Mật khẩu"), { target: { value: "wrong-password" } });
    fireEvent.click(screen.getByRole("button", { name: "Đăng nhập" }));

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Tên đăng nhập hoặc mật khẩu không đúng.");
    expect(alert).toHaveTextContent("Mã yêu cầu: 123e4567-e89b-42d3-a456-426614174000");
  });

  it("binds canonical password validation details to their owning fields", async () => {
    controls.changePassword.mockRejectedValue({
      kind: "canonical",
      errorCode: "VALIDATION_FAILED",
      message: "ignored server copy",
      details: {
        current_password: ["Mật khẩu hiện tại không đúng."],
        new_password: ["Mật khẩu mới chưa đủ mạnh."],
      },
      requestId: "123e4567-e89b-42d3-a456-426614174001",
    });
    render(<ChangePasswordForm />);
    fireEvent.change(screen.getByLabelText("Mật khẩu hiện tại"), {
      target: { value: "OldPassword123!" },
    });
    fireEvent.change(screen.getByLabelText("Mật khẩu mới"), {
      target: { value: "NewPassword456!" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Đổi mật khẩu" }));

    expect(await screen.findByText("Mật khẩu hiện tại không đúng.")).toBeInTheDocument();
    expect(screen.getByText("Mật khẩu mới chưa đủ mạnh.")).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent("Dữ liệu không hợp lệ.");
  });
});

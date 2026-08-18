import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { UserDirectory } from "@/features/identity/ui/UserDirectory";

const hasCapability = vi.fn<(value: string) => boolean>();
vi.mock("@/features/identity/model/AuthProvider", () => ({
  useAuth: () => ({ hasCapability }),
}));
vi.mock("@/features/identity/api/identity-api", () => ({
  listUsers: vi.fn().mockResolvedValue({ results: [] }),
  changeUserRole: vi.fn(),
  changeUserStatus: vi.fn(),
  resetUserPassword: vi.fn(),
  createUser: vi.fn(),
}));

afterEach(() => {
  cleanup();
  hasCapability.mockReset();
});

describe("capability presentation", () => {
  it("hides administration without the exact user.view capability", () => {
    hasCapability.mockReturnValue(false);
    render(<UserDirectory />);
    expect(screen.getByText("Bạn không có quyền xem danh bạ.")).toBeInTheDocument();
  });

  it("does not infer known controls from an unknown future capability", () => {
    hasCapability.mockImplementation((value) => value === "future.permission");
    render(<UserDirectory />);
    expect(screen.queryByText("Tạo người dùng")).not.toBeInTheDocument();
  });
});

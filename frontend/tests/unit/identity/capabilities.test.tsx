import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { IdentityRouteBoundary } from "@/features/identity/model/IdentityRouteBoundary";
import { UserDirectory } from "@/features/identity/ui/UserDirectory";

const controls = vi.hoisted(() => ({
  hasCapability: vi.fn<(value: string) => boolean>(),
  state: {
    kind: "authenticated" as const,
    account: { capabilities: [] as string[] },
  },
  replace: vi.fn(),
}));
vi.mock("@/features/identity/model/AuthProvider", () => ({
  useAuth: () => ({ hasCapability: controls.hasCapability, state: controls.state }),
}));
vi.mock("next/navigation", () => ({ useRouter: () => ({ replace: controls.replace }) }));
vi.mock("@/features/identity/api/identity-api", () => ({
  listUsers: vi.fn().mockResolvedValue({ results: [] }),
  changeUserRole: vi.fn(),
  changeUserStatus: vi.fn(),
  resetUserPassword: vi.fn(),
  createUser: vi.fn(),
}));

afterEach(() => {
  cleanup();
  controls.hasCapability.mockReset();
  controls.state.account.capabilities = [];
  controls.replace.mockReset();
});

describe("capability presentation", () => {
  it("hides administration without the exact user.view capability", () => {
    controls.hasCapability.mockReturnValue(false);
    render(<UserDirectory />);
    expect(screen.getByText("Bạn không có quyền xem danh bạ.")).toBeInTheDocument();
  });

  it("does not infer known controls from an unknown future capability", () => {
    controls.hasCapability.mockImplementation((value) => value === "future.permission");
    render(<UserDirectory />);
    expect(screen.queryByText("Tạo người dùng")).not.toBeInTheDocument();
  });

  it("maps job-health route only to operations.job_health.view", () => {
    controls.state.account.capabilities = ["operations.job_health.view"];
    render(
      <IdentityRouteBoundary route="job-health">
        <p>Health content</p>
      </IdentityRouteBoundary>,
    );
    expect(screen.getByText("Health content")).toBeInTheDocument();
    expect(controls.replace).not.toHaveBeenCalled();
  });
});

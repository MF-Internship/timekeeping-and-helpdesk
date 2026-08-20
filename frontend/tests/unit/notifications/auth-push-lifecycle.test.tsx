import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const api = vi.hoisted(() => ({ refresh: vi.fn(), getMe: vi.fn(), logout: vi.fn() }));
const clearPushForAccount = vi.hoisted(() => vi.fn());
vi.mock("@/features/identity/api/identity-api", () => ({
  ...api,
  login: vi.fn(),
  changePassword: vi.fn(),
}));
vi.mock("@/features/notifications/adapters/browser-push", () => ({ clearPushForAccount }));

import { AuthProvider, useAuth } from "@/features/identity/model/AuthProvider";
import { setSessionState } from "@/features/identity/model/session-store";

function Logout() {
  const auth = useAuth();
  return <button onClick={() => void auth.logout()}>logout {auth.state.kind}</button>;
}

beforeEach(() => {
  vi.clearAllMocks();
  setSessionState({ kind: "loading" });
  api.refresh.mockResolvedValue({ access: "access" });
  api.getMe.mockResolvedValue({
    id: 17,
    username: "employee",
    full_name: "Employee",
    phone: null,
    email: null,
    role: "HELPDESK",
    is_active: true,
    must_change_password: false,
    capabilities: [],
  });
  clearPushForAccount.mockResolvedValue(undefined);
});

describe("push authentication lifecycle", () => {
  it("waits for server logout before local browser cleanup", async () => {
    let release!: () => void;
    api.logout.mockReturnValue(
      new Promise<void>((resolve) => {
        release = resolve;
      }),
    );
    render(
      <AuthProvider>
        <Logout />
      </AuthProvider>,
    );
    await screen.findByText("logout authenticated");
    fireEvent.click(screen.getByRole("button"));
    expect(api.logout).toHaveBeenCalledOnce();
    expect(clearPushForAccount).not.toHaveBeenCalled();
    release();
    await waitFor(() => expect(clearPushForAccount).toHaveBeenCalledWith(17));
    expect(screen.getByText("logout anonymous")).toBeInTheDocument();
  });
});

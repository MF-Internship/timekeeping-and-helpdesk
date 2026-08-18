import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AuthProvider, useAuth } from "@/features/identity/model/AuthProvider";
import { IdentityRouteBoundary } from "@/features/identity/model/IdentityRouteBoundary";
import { setSessionState } from "@/features/identity/model/session-store";
import { authenticatedFetch } from "@/shared/transport/authenticated-fetch";

const navigation = vi.hoisted(() => ({ replace: vi.fn() }));
vi.mock("next/navigation", () => ({ useRouter: () => navigation }));

const api = vi.hoisted(() => ({
  refresh: vi.fn(),
  getMe: vi.fn(),
  login: vi.fn(),
  logout: vi.fn(),
  changePassword: vi.fn(),
}));

vi.mock("@/features/identity/api/identity-api", () => api);

function Probe() {
  return <output>{useAuth().state.kind}</output>;
}

const account = {
  id: 1,
  username: "manager",
  full_name: "Manager",
  phone: null,
  email: null,
  role: "MANAGER",
  is_active: true,
  must_change_password: false,
  capabilities: ["user.view"],
};

beforeEach(() => {
  setSessionState({ kind: "loading" });
  api.refresh.mockReset();
  api.getMe.mockReset();
  navigation.replace.mockReset();
  vi.unstubAllGlobals();
});
afterEach(cleanup);

describe("AuthProvider bootstrap", () => {
  it("refreshes once, loads me, and keeps the authenticated account in memory", async () => {
    api.refresh.mockResolvedValue({ access: "memory-access" });
    api.getMe.mockResolvedValue({
      id: 1,
      username: "manager",
      full_name: "Manager",
      phone: null,
      email: null,
      role: "MANAGER",
      is_active: true,
      must_change_password: false,
      last_login: null,
      created_at: "2026-08-18T00:00:00Z",
      capabilities: ["user.view"],
    });
    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );
    await waitFor(() => expect(screen.getByText("authenticated")).toBeInTheDocument());
    expect(api.refresh).toHaveBeenCalledTimes(1);
    expect(api.getMe).toHaveBeenCalledTimes(1);
    expect(localStorage).toHaveLength(0);
  });

  it("stops at anonymous when bootstrap refresh is unavailable", async () => {
    api.refresh.mockRejectedValue(new Error("unavailable"));
    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );
    await waitFor(() => expect(screen.getByText("anonymous")).toBeInTheDocument());
    expect(api.getMe).not.toHaveBeenCalled();
  });

  it("enters inactive and clears bootstrap access when current account is locked", async () => {
    api.refresh.mockRejectedValue({ error_code: "ACCOUNT_INACTIVE" });
    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );
    await waitFor(() => expect(screen.getByText("inactive")).toBeInTheDocument());
    expect(api.getMe).not.toHaveBeenCalled();
  });

  it("keeps a forced bootstrap anonymous until login restores an access token", async () => {
    api.refresh.mockRejectedValue({ error_code: "PASSWORD_CHANGE_REQUIRED" });
    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );
    await waitFor(() => expect(screen.getByText("anonymous")).toBeInTheDocument());
    expect(api.getMe).not.toHaveBeenCalled();
  });

  it.each([
    ["INVALID_TOKEN", "anonymous", 2],
    ["ACCOUNT_INACTIVE", "inactive", 1],
    ["PASSWORD_CHANGE_REQUIRED", "forced_change", 1],
  ])("maps a transport %s failure into %s without a retry loop", async (code, state, calls) => {
    api.refresh.mockResolvedValue({ access: "memory-access" });
    api.getMe.mockResolvedValue({
      id: 1,
      username: "manager",
      full_name: "Manager",
      phone: null,
      email: null,
      role: "MANAGER",
      is_active: true,
      must_change_password: false,
      capabilities: ["user.view"],
    });
    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );
    await screen.findByText("authenticated");
    const status = code === "PASSWORD_CHANGE_REQUIRED" ? 403 : 401;
    const platformFetch = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify({ error_code: code }), { status }));
    vi.stubGlobal("fetch", platformFetch);

    await authenticatedFetch("/api/v1/users/");

    await waitFor(() => expect(screen.getByText(state)).toBeInTheDocument());
    expect(platformFetch).toHaveBeenCalledTimes(calls);
  });

  it("does not render or fetch a capability-protected route before redirect", async () => {
    api.refresh.mockResolvedValue({ access: "memory-access" });
    api.getMe.mockResolvedValue({
      id: 2,
      username: "leader",
      full_name: "Leader",
      phone: null,
      email: null,
      role: "LEADER",
      is_active: true,
      must_change_password: false,
      capabilities: [],
    });
    const protectedWork = vi.fn();
    function ProtectedChild() {
      protectedWork();
      return <p>directory</p>;
    }
    render(
      <AuthProvider>
        <IdentityRouteBoundary route="users">
          <ProtectedChild />
        </IdentityRouteBoundary>
      </AuthProvider>,
    );

    await waitFor(() => expect(navigation.replace).toHaveBeenCalledWith("/"));
    expect(protectedWork).not.toHaveBeenCalled();
    expect(screen.queryByText("directory")).not.toBeInTheDocument();
  });

  it("keeps login anonymous-only and redirects an authenticated account", async () => {
    api.refresh.mockResolvedValue({ access: "memory-access" });
    api.getMe.mockResolvedValue(account);
    render(
      <AuthProvider>
        <IdentityRouteBoundary route="login">
          <p>login business UI</p>
        </IdentityRouteBoundary>
      </AuthProvider>,
    );

    await waitFor(() => expect(navigation.replace).toHaveBeenCalledWith("/"));
    expect(screen.queryByText("login business UI")).not.toBeInTheDocument();
  });

  it("allows only password change while the account is forced", async () => {
    api.refresh.mockResolvedValue({ access: "memory-access" });
    api.getMe.mockResolvedValue({ ...account, must_change_password: true });
    render(
      <AuthProvider>
        <IdentityRouteBoundary route="change-password">
          <p>password business UI</p>
        </IdentityRouteBoundary>
      </AuthProvider>,
    );

    expect(await screen.findByText("password business UI")).toBeInTheDocument();
    expect(navigation.replace).not.toHaveBeenCalled();
  });

  it("redirects anonymous protected routes before their UI renders", async () => {
    api.refresh.mockRejectedValue(new Error("no session"));
    render(
      <AuthProvider>
        <IdentityRouteBoundary route="change-password">
          <p>password business UI</p>
        </IdentityRouteBoundary>
      </AuthProvider>,
    );

    await waitFor(() => expect(navigation.replace).toHaveBeenCalledWith("/login"));
    expect(screen.queryByText("password business UI")).not.toBeInTheDocument();
  });
});

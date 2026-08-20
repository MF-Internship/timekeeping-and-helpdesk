import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const navigation = vi.hoisted(() => ({ replace: vi.fn() }));
const api = vi.hoisted(() => ({
  resolveNotificationTarget: vi.fn(),
  markNotificationRead: vi.fn(),
}));
vi.mock("next/navigation", () => ({
  useParams: () => ({ reference: "9d872350-aa60-4aaa-8a4d-e3a26708a302" }),
  useRouter: () => navigation,
}));
vi.mock("@/features/notifications/api/notification-api", () => api);
vi.mock("@/features/identity/model/IdentityRouteBoundary", () => ({
  IdentityRouteBoundary: ({ children }: { children: React.ReactNode }) => children,
}));

import NotificationOpenPage from "@/app/notifications/open/[reference]/page";

beforeEach(() => vi.clearAllMocks());

describe("authorization-safe notification open", () => {
  it("navigates to an already-authorized Task focus only after resolver success", async () => {
    api.resolveNotificationTarget.mockResolvedValue({ destination: "TASK", target_id: 42 });
    render(<NotificationOpenPage />);
    expect(screen.getByRole("status")).toHaveTextContent("kiểm tra quyền");
    await waitFor(() => expect(navigation.replace).toHaveBeenCalledWith("/tasks?focus=42"));
    expect(api.markNotificationRead).not.toHaveBeenCalled();
  });

  it("stays on a non-disclosing denial without target navigation", async () => {
    api.resolveNotificationTarget.mockRejectedValue(new Error("not found"));
    render(<NotificationOpenPage />);
    expect(await screen.findByRole("alert")).toHaveTextContent("không còn quyền truy cập");
    expect(navigation.replace).not.toHaveBeenCalled();
  });
});

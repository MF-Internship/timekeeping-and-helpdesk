import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useTaskManagement } from "@/features/tasks/model/use-task-management";

import { groupedFixture } from "./fixtures";

const controls = vi.hoisted(() => ({
  list: vi.fn(),
  override: vi.fn(),
  detail: vi.fn(),
}));
vi.mock("@/features/tasks/api/task-api", async (load) => ({
  ...(await load()),
  listTasks: controls.list,
  completeTaskOverride: controls.override,
  getTask: controls.detail,
}));
vi.mock("@/features/identity/model/AuthProvider", () => ({
  useAuth: () => ({ hasCapability: () => false }),
}));
vi.mock("@/features/identity/api/identity-api", () => ({
  listUsers: vi.fn().mockResolvedValue({ results: [] }),
}));
vi.mock("@/features/locations/api/location-api", () => ({
  listLocations: vi.fn().mockResolvedValue([]),
}));

beforeEach(() => {
  controls.list.mockReset().mockResolvedValue(groupedFixture());
  controls.override.mockReset();
  controls.detail.mockReset().mockResolvedValue({ id: 1 });
});

describe("Task mutation orchestration", () => {
  it("does not automatically retry and refetches after TASK_ALREADY_COMPLETED", async () => {
    controls.override.mockRejectedValue({
      kind: "canonical",
      errorCode: "TASK_ALREADY_COMPLETED",
      message: "Đã hoàn thành",
      details: {},
      requestId: "request",
    });
    const { result } = renderHook(() => useTaskManagement());
    await waitFor(() => expect(controls.list).toHaveBeenCalledTimes(1));
    await act(async () => {
      await Promise.all([
        result.current.override(1, { completion_note: "x" }),
        result.current.override(1, { completion_note: "x" }),
      ]);
    });
    expect(controls.override).toHaveBeenCalledTimes(1);
    expect(controls.list).toHaveBeenCalledTimes(2);
    expect(controls.detail).toHaveBeenCalledWith(1);
    expect(result.current.mutation.kind).toBe("failed");
  });
});

import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  completeTaskOverride,
  completeTaskField,
  createEvidenceUpload,
  createTask,
  listTasks,
  updateTaskStatus,
} from "@/features/tasks/api/task-api";

const client = vi.hoisted(() => ({
  GET: vi.fn(),
  POST: vi.fn(),
  PATCH: vi.fn(),
}));
vi.mock("@/shared/api/client", () => ({ apiClient: client }));

beforeEach(() => {
  client.GET.mockReset().mockResolvedValue({ data: { overdue: [] }, response: new Response() });
  client.POST.mockReset().mockResolvedValue({ data: { id: 1 }, response: new Response() });
  client.PATCH.mockReset().mockResolvedValue({ data: { id: 1 }, response: new Response() });
});

describe("Task generated-client wrappers", () => {
  it("loads the server-owned grouped projection", async () => {
    await listTasks();
    expect(client.GET).toHaveBeenCalledWith("/api/v1/tasks/");
  });

  it("sends one create request with the wire-format body", async () => {
    const body = {
      title: "Việc",
      description: "",
      assigned_date: "2026-08-20",
      assignee_ids: [2, 3],
    };
    await createTask(body);
    expect(client.POST).toHaveBeenCalledTimes(1);
    expect(client.POST).toHaveBeenCalledWith("/api/v1/tasks/", { body });
  });

  it("uses dedicated lifecycle and override operations", async () => {
    await updateTaskStatus(7, { status: "BLOCKED", block_reason: "Chờ linh kiện" });
    await completeTaskOverride(7, { completion_note: "Đã xử lý" });
    expect(client.POST.mock.calls).toEqual([
      [
        "/api/v1/tasks/{task_id}/status",
        {
          params: { path: { task_id: "7" } },
          body: { status: "BLOCKED", block_reason: "Chờ linh kiện" },
        },
      ],
      [
        "/api/v1/tasks/{task_id}/complete-override",
        { params: { path: { task_id: "7" } }, body: { completion_note: "Đã xử lý" } },
      ],
    ]);
  });

  it("uses evidence intent and an explicit idempotency header for field completion", async () => {
    await createEvidenceUpload(7, {
      mime: "image/jpeg",
      size_bytes: 3,
      checksum_sha256: "a".repeat(64),
    });
    await completeTaskField(
      7,
      {
        upload_ids: ["00000000-0000-4000-8000-000000000001"],
        latitude: "10",
        longitude: "106",
        accuracy_m: "12",
        captured_at: "2026-08-20T10:00:00Z",
      },
      "submission-1",
    );
    expect(client.POST.mock.calls.at(-2)?.[0]).toBe("/api/v1/tasks/{task_id}/evidence-uploads");
    expect(client.POST.mock.calls.at(-1)).toEqual([
      "/api/v1/tasks/{task_id}/complete-field",
      {
        params: { path: { task_id: "7" }, header: { "Idempotency-Key": "submission-1" } },
        body: {
          upload_ids: ["00000000-0000-4000-8000-000000000001"],
          latitude: "10",
          longitude: "106",
          accuracy_m: "12",
          captured_at: "2026-08-20T10:00:00Z",
        },
      },
    ]);
  });
});

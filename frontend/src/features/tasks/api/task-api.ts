import { apiClient } from "@/shared/api/client";
import type { components, operations } from "@/shared/api/schema";
import { parseApiResultFailure } from "@/shared/errors/api-error";

export type GroupedTaskList = components["schemas"]["GroupedTaskList"];
export type TaskCreateInput = NonNullable<
  operations["tasks_create"]["requestBody"]
>["content"]["application/json"];
export type TaskDetail = components["schemas"]["TaskDetail"];
export type TaskItem = components["schemas"]["TaskItem"];
export type TaskOverrideInput = NonNullable<
  operations["tasks_complete_override_create"]["requestBody"]
>["content"]["application/json"];
export type TaskStatusInput = NonNullable<
  operations["tasks_status_create"]["requestBody"]
>["content"]["application/json"];
export type TaskUpdateInput = NonNullable<
  operations["tasks_partial_update"]["requestBody"]
>["content"]["application/json"];
export type EvidenceUploadInput = components["schemas"]["EvidenceUpload"];
export type TaskFieldCompletionInput = components["schemas"]["TaskFieldCompletion"];

async function unwrap<T>(result: { data?: T; error?: unknown; response: Response }): Promise<T> {
  if (result.data === undefined) throw await parseApiResultFailure(result);
  return result.data;
}

export async function listTasks() {
  return await unwrap(await apiClient.GET("/api/v1/tasks/"));
}

export async function createTask(body: TaskCreateInput) {
  return await unwrap(await apiClient.POST("/api/v1/tasks/", { body }));
}

export async function getTask(taskId: number) {
  return await unwrap(
    await apiClient.GET("/api/v1/tasks/{task_id}/", {
      params: { path: { task_id: String(taskId) } },
    }),
  );
}

export async function updateTask(taskId: number, body: TaskUpdateInput) {
  return await unwrap(
    await apiClient.PATCH("/api/v1/tasks/{task_id}/", {
      params: { path: { task_id: String(taskId) } },
      body,
    }),
  );
}

export async function deleteTask(taskId: number) {
  const result = await apiClient.DELETE("/api/v1/tasks/{task_id}/", {
    params: { path: { task_id: String(taskId) } },
  });
  if (!result.response.ok) throw await parseApiResultFailure(result);
}

export async function updateTaskStatus(taskId: number, body: TaskStatusInput) {
  return await unwrap(
    await apiClient.POST("/api/v1/tasks/{task_id}/status", {
      params: { path: { task_id: String(taskId) } },
      body,
    }),
  );
}

export async function completeTaskOverride(taskId: number, body: TaskOverrideInput) {
  return await unwrap(
    await apiClient.POST("/api/v1/tasks/{task_id}/complete-override", {
      params: { path: { task_id: String(taskId) } },
      body,
    }),
  );
}

export async function createEvidenceUpload(taskId: number, body: EvidenceUploadInput) {
  return await unwrap(await apiClient.POST("/api/v1/tasks/{task_id}/evidence-uploads", {
    params: { path: { task_id: String(taskId) } },
    body,
  }));
}

export async function uploadEvidenceFile(
  intent: components["schemas"]["EvidenceUploadIntent"],
  file: File,
) {
  const response = await fetch(intent.upload_url, { method: "PUT", headers: intent.headers, body: file });
  if (!response.ok) throw new Error("Không thể tải ảnh minh chứng lên kho lưu trữ.");
}

export async function completeTaskField(
  taskId: number,
  body: TaskFieldCompletionInput,
  idempotencyKey: string,
) {
  return await unwrap(await apiClient.POST("/api/v1/tasks/{task_id}/complete-field", {
    params: { path: { task_id: String(taskId) }, header: { "Idempotency-Key": idempotencyKey } },
    body,
  }));
}

export async function accessTaskPhoto(taskId: number, photoId: number) {
  return await unwrap(await apiClient.POST("/api/v1/tasks/{task_id}/photos/{photo_id}/access", {
    params: { path: { task_id: String(taskId), photo_id: String(photoId) } },
  }));
}

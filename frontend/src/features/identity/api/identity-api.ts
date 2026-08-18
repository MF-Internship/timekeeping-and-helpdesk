import { apiClient } from "@/shared/api/client";
import { parseApiResultFailure } from "@/shared/errors/api-error";

export type LoginInput = { username: string; password: string };
export type ProfileInput = { full_name?: string; phone?: string | null; email?: string | null };
export type UserCreateInput = {
  username: string;
  full_name: string;
  role: string;
  phone?: string | null;
  email?: string | null;
};

async function unwrap<T>(result: { data?: T; error?: unknown; response: Response }): Promise<T> {
  if (result.data === undefined) throw await parseApiResultFailure(result);
  return result.data;
}

async function ensureSuccess(result: { error?: unknown; response: Response }): Promise<void> {
  if (!result.response.ok) throw await parseApiResultFailure(result);
}

export async function login(input: LoginInput) {
  return await unwrap(await apiClient.POST("/api/v1/auth/login", { body: input }));
}

export async function refresh() {
  return await unwrap(await apiClient.POST("/api/v1/auth/refresh"));
}

export async function logout() {
  await ensureSuccess(await apiClient.POST("/api/v1/auth/logout"));
}

export async function getMe() {
  return await unwrap(await apiClient.GET("/api/v1/me/"));
}

export async function updateMe(input: ProfileInput) {
  return await unwrap(await apiClient.PATCH("/api/v1/me/", { body: input }));
}

export async function changePassword(current_password: string, new_password: string) {
  return await unwrap(
    await apiClient.POST("/api/v1/change-password", {
      body: { current_password, new_password },
    }),
  );
}

export async function listUsers(query: {
  q?: string;
  role?: string;
  is_active?: boolean;
  page?: number;
}) {
  return await unwrap(await apiClient.GET("/api/v1/users/", { params: { query } }));
}

export async function createUser(input: UserCreateInput) {
  return await unwrap(await apiClient.POST("/api/v1/users/", { body: input }));
}

export async function updateUser(user_id: number, input: ProfileInput) {
  return await unwrap(
    await apiClient.PATCH("/api/v1/users/{user_id}/", {
      params: { path: { user_id: String(user_id) } },
      body: input,
    }),
  );
}

export async function changeUserRole(user_id: number, role: string) {
  return await unwrap(
    await apiClient.PATCH("/api/v1/users/{user_id}/role", {
      params: { path: { user_id: String(user_id) } },
      body: { role },
    }),
  );
}

export async function changeUserStatus(user_id: number, is_active: boolean) {
  return await unwrap(
    await apiClient.PATCH("/api/v1/users/{user_id}/status", {
      params: { path: { user_id: String(user_id) } },
      body: { is_active },
    }),
  );
}

export async function resetUserPassword(user_id: number) {
  return await unwrap(
    await apiClient.POST("/api/v1/users/{user_id}/reset-password", {
      params: { path: { user_id: String(user_id) } },
    }),
  );
}

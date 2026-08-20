import type { ApiFailure } from "@/shared/errors/api-error";

import type { GroupedTaskList, TaskItem } from "../api/task-api";

export type TaskCapabilities = {
  canCreateSelf: boolean;
  canAssign: boolean;
  canUpdateSelf: boolean;
  canUpdateAny: boolean;
  canDeleteSelf: boolean;
  canOverride: boolean;
  canCompleteField: boolean;
};

export type TaskLoadState =
  | { kind: "loading" }
  | { kind: "failed"; error: unknown }
  | { kind: "ready"; data: GroupedTaskList; refreshError?: unknown };

export type TaskMutationState =
  | { kind: "idle" }
  | { kind: "submitting" }
  | { kind: "failed"; error: unknown }
  | { kind: "succeeded"; message: string };

export const TASK_GROUPS = ["overdue", "today", "upcoming", "completed"] as const;
export type TaskGroupKey = (typeof TASK_GROUPS)[number];

export function isTaskConflict(error: unknown): error is ApiFailure & { kind: "canonical" } {
  return (
    typeof error === "object" &&
    error !== null &&
    "kind" in error &&
    "errorCode" in error &&
    error.kind === "canonical" &&
    error.errorCode === "TASK_ALREADY_COMPLETED"
  );
}

export function taskCount(data: GroupedTaskList): number {
  return TASK_GROUPS.reduce((count, group) => count + data[group].length, 0);
}

export function taskById(data: GroupedTaskList, taskId: number): TaskItem | undefined {
  return TASK_GROUPS.flatMap((group) => data[group]).find((task) => task.id === taskId);
}

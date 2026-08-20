"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { listUsers } from "@/features/identity/api/identity-api";
import { useAuth } from "@/features/identity/model/AuthProvider";
import { listLocations } from "@/features/locations/api/location-api";
import { UI_MESSAGES } from "@/shared/messages";

import * as taskApi from "../api/task-api";
import { isTaskConflict, type TaskLoadState, type TaskMutationState } from "./task-state";

type UserPage = Awaited<ReturnType<typeof listUsers>>;
type LocationList = Awaited<ReturnType<typeof listLocations>>;
type Mutation = () => Promise<unknown>;

function useTaskList() {
  const [loadState, setLoadState] = useState<TaskLoadState>({ kind: "loading" });
  const refresh = useCallback(async () => {
    try {
      setLoadState({ kind: "ready", data: await taskApi.listTasks() });
    } catch (error) {
      setLoadState((current) =>
        current.kind === "ready" ? { ...current, refreshError: error } : { kind: "failed", error },
      );
    }
  }, []);
  useEffect(() => queueMicrotask(() => void refresh()), [refresh]);
  return { loadState, refresh };
}

function useTaskReferences(canAssign: boolean, loadLocations: boolean) {
  const [users, setUsers] = useState<UserPage["results"]>([]);
  const [locations, setLocations] = useState<LocationList>([]);
  useEffect(() => {
    if (loadLocations) {
      void listLocations({ is_active: true }).then(setLocations).catch(clearLocations);
    }
    if (canAssign) {
      void listUsers({ role: "HELPDESK", is_active: true }).then((page) => setUsers(page.results));
    }
    function clearLocations() {
      setLocations([]);
    }
  }, [canAssign, loadLocations]);
  return { users, locations };
}

function useTaskMutation(refresh: () => Promise<void>) {
  const [mutation, setMutation] = useState<TaskMutationState>({ kind: "idle" });
  const flight = useRef(false);
  const runMutation = useCallback(
    async (
      operation: Mutation,
      successMessage: string,
      conflictRefresh?: Mutation,
      propagate = false,
    ) => {
      if (flight.current) return;
      flight.current = true;
      setMutation({ kind: "submitting" });
      try {
        await operation();
        await refresh();
        setMutation({ kind: "succeeded", message: successMessage });
      } catch (error) {
        if (isTaskConflict(error)) {
          await Promise.all([refresh(), conflictRefresh?.()]);
        }
        setMutation({ kind: "failed", error });
        if (propagate) throw error;
      } finally {
        flight.current = false;
      }
    },
    [refresh],
  );
  return { mutation, runMutation };
}

export function useTaskManagement() {
  const auth = useAuth();
  const canAssign = auth.hasCapability("task.create.assign");
  const canEdit = auth.hasCapability("task.update.self") || auth.hasCapability("task.update.any");
  const list = useTaskList();
  const references = useTaskReferences(
    canAssign,
    canAssign || canEdit || auth.hasCapability("task.create.self"),
  );
  const commands = useTaskMutation(list.refresh);
  const capabilities = taskCapabilities(auth, canAssign);
  const accountId = auth.state?.kind === "authenticated" ? auth.state.account.id : 0;
  return taskManagement({ ...list, ...references, ...commands, capabilities, accountId });
}

function taskCapabilities(auth: ReturnType<typeof useAuth>, canAssign: boolean) {
  return {
    canCreateSelf: auth.hasCapability("task.create.self"),
    canAssign,
    canUpdateSelf: auth.hasCapability("task.update.self"),
    canUpdateAny: auth.hasCapability("task.update.any"),
    canDeleteSelf: auth.hasCapability("task.delete.self"),
    canOverride: auth.hasCapability("task.complete.override"),
    canCompleteField: auth.hasCapability("task.complete.field"),
  };
}

type ManagementContext = ReturnType<typeof useTaskList> &
  ReturnType<typeof useTaskReferences> &
  ReturnType<typeof useTaskMutation> & {
    capabilities: ReturnType<typeof taskCapabilities>;
    accountId: number;
  };

function taskManagement(context: ManagementContext) {
  const run = context.runMutation;
  return {
    ...context,
    create: (body: taskApi.TaskCreateInput) =>
      run(() => taskApi.createTask(body), UI_MESSAGES.tasks.created, undefined, true),
    remove: (taskId: number) => run(() => taskApi.deleteTask(taskId), "Đã xóa công việc tự tạo."),
    update: (taskId: number, body: taskApi.TaskUpdateInput) =>
      run(() => taskApi.updateTask(taskId, body), UI_MESSAGES.tasks.saved),
    changeStatus: (taskId: number, body: taskApi.TaskStatusInput) =>
      run(() => taskApi.updateTaskStatus(taskId, body), UI_MESSAGES.tasks.statusSaved),
    override: (taskId: number, body: taskApi.TaskOverrideInput) =>
      run(
        () => taskApi.completeTaskOverride(taskId, body),
        UI_MESSAGES.tasks.completed,
        () => taskApi.getTask(taskId),
      ),
    completeField: (taskId: number, body: taskApi.TaskFieldCompletionInput, key: string) =>
      run(
        () => taskApi.completeTaskField(taskId, body, key),
        UI_MESSAGES.tasks.completed,
        () => taskApi.getTask(taskId),
        true,
      ),
    detail: taskApi.getTask,
  };
}

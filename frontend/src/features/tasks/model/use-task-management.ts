"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { listUsers } from "@/features/identity/api/identity-api";
import { useAuth } from "@/features/identity/model/AuthProvider";
import { listLocations } from "@/features/locations/api/location-api";
import { UI_MESSAGES } from "@/shared/messages";
import { readUserCache, writeUserCache } from "@/shared/cache/user-resource-cache";

import * as taskApi from "../api/task-api";
import { isTaskConflict, type TaskLoadState, type TaskMutationState } from "./task-state";

type UserPage = Awaited<ReturnType<typeof listUsers>>;
type LocationList = Awaited<ReturnType<typeof listLocations>>;
type Mutation = () => Promise<unknown>;

function useTaskList(accountId: number | undefined) {
  const [loadState, setLoadState] = useState<TaskLoadState>(() => cachedTaskState(accountId));
  const accountRef = useRef(accountId);
  const refresh = useCallback(async () => {
    const requestedAccount = accountId;
    try {
      const data = await taskApi.listTasks();
      if (accountRef.current !== requestedAccount) return;
      writeUserCache(requestedAccount, "tasks", data);
      setLoadState({ kind: "ready", data });
    } catch (error) {
      if (accountRef.current !== requestedAccount) return;
      setLoadState((current) =>
        current.kind === "ready" ? { ...current, refreshError: error } : { kind: "failed", error },
      );
    }
  }, [accountId]);
  useEffect(() => {
    accountRef.current = accountId;
    queueMicrotask(() => {
      setLoadState(cachedTaskState(accountId));
      void refresh();
    });
  }, [accountId, refresh]);
  return { loadState, refresh };
}

function cachedTaskState(accountId: number | undefined): TaskLoadState {
  const cached = readUserCache<Awaited<ReturnType<typeof taskApi.listTasks>>>(accountId, "tasks");
  return cached ? { kind: "ready", data: cached } : { kind: "loading" };
}

function useTaskReferences(
  accountId: number | undefined,
  canAssign: boolean,
  loadLocations: boolean,
) {
  const users = useTaskUsers(accountId, canAssign);
  const locations = useTaskLocations(accountId, loadLocations);
  return { users, locations };
}

function useTaskUsers(accountId: number | undefined, enabled: boolean) {
  const [users, setUsers] = useState<UserPage["results"]>(
    () => readUserCache<UserPage["results"]>(accountId, "task-assignees") ?? [],
  );
  useEffect(() => {
    let active = true;
    queueMicrotask(() => active && setUsers(cachedUsers(accountId, enabled)));
    if (enabled) {
      void listUsers({ role: "HELPDESK", is_active: true })
        .then((page) => {
          if (!active) return;
          setUsers(page.results);
          writeUserCache(accountId, "task-assignees", page.results);
        })
        .catch(() => undefined);
    }
    return () => {
      active = false;
    };
  }, [accountId, enabled]);
  return users;
}

function cachedUsers(accountId: number | undefined, enabled: boolean) {
  return enabled ? (readUserCache<UserPage["results"]>(accountId, "task-assignees") ?? []) : [];
}

function useTaskLocations(accountId: number | undefined, enabled: boolean) {
  const [locations, setLocations] = useState<LocationList>(
    () => readUserCache<LocationList>(accountId, "task-locations") ?? [],
  );
  useEffect(() => {
    let active = true;
    queueMicrotask(() => active && setLocations(cachedLocations(accountId, enabled)));
    if (enabled) {
      void listLocations({ is_active: true })
        .then((values) => {
          if (!active) return;
          setLocations(values);
          writeUserCache(accountId, "task-locations", values);
        })
        .catch(() => undefined);
    }
    return () => {
      active = false;
    };
  }, [accountId, enabled]);
  return locations;
}

function cachedLocations(accountId: number | undefined, enabled: boolean) {
  return enabled ? (readUserCache<LocationList>(accountId, "task-locations") ?? []) : [];
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
        await refreshTaskConflict(error, refresh, conflictRefresh);
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

async function refreshTaskConflict(error: unknown, refresh: Mutation, conflictRefresh?: Mutation) {
  if (isTaskConflict(error)) await Promise.all([refresh(), conflictRefresh?.()]);
}

export function useTaskManagement() {
  const auth = useAuth();
  const accountId = auth.state?.kind === "authenticated" ? auth.state.account.id : undefined;
  const canAssign = auth.hasCapability("task.create.assign");
  const canEdit = auth.hasCapability("task.update.self") || auth.hasCapability("task.update.any");
  const list = useTaskList(accountId);
  const references = useTaskReferences(
    accountId,
    canAssign,
    canAssign || canEdit || auth.hasCapability("task.create.self"),
  );
  const commands = useTaskMutation(list.refresh);
  const capabilities = taskCapabilities(auth, canAssign);
  return taskManagement({
    ...list,
    ...references,
    ...commands,
    capabilities,
    accountId: accountId ?? 0,
  });
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

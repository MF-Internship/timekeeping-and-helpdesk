import type { GroupedTaskList, TaskItem } from "@/features/tasks/api/task-api";

export function taskFixture(overrides: Partial<TaskItem> = {}): TaskItem {
  return {
    id: 1,
    title: "Kiểm tra máy in",
    description: "Tầng 2",
    created_by: { id: 9, full_name: "Quản lý" },
    assigned_date: "2026-08-19",
    status: "TODO",
    location: null,
    assignees: [{ user: { id: 3, full_name: "An" }, assigned_at: "2026-08-18T08:00:00Z" }],
    completed_by: null,
    completed_at: null,
    completion_method: null,
    completion_note: null,
    block_reason: null,
    group: "OVERDUE",
    overdue_days: 1,
    ...overrides,
  } as TaskItem;
}

export function groupedFixture(overrides: Partial<GroupedTaskList> = {}): GroupedTaskList {
  return {
    business_date: "2026-08-20",
    overdue: [],
    today: [],
    upcoming: [],
    completed: [],
    ...overrides,
  } as GroupedTaskList;
}

export function managementFixture(overrides: Record<string, unknown> = {}) {
  return {
    loadState: { kind: "ready", data: groupedFixture() },
    mutation: { kind: "idle" },
    users: [],
    locations: [],
    accountId: 0,
    capabilities: {
      canCreateSelf: false,
      canAssign: false,
      canUpdateSelf: false,
      canUpdateAny: false,
      canDeleteSelf: false,
      canOverride: false,
      canCompleteField: false,
    },
    refresh: async () => undefined,
    create: async () => undefined,
    update: async () => undefined,
    remove: async () => undefined,
    changeStatus: async () => undefined,
    override: async () => undefined,
    completeField: async () => undefined,
    detail: async () => ({ ...taskFixture(), updates: [] }),
    ...overrides,
  };
}

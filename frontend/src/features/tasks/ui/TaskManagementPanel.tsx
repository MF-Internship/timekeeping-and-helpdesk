"use client";

import { useEffect, useRef, useState } from "react";
import * as Tabs from "@radix-ui/react-tabs";

import { UI_MESSAGES } from "@/shared/messages";
import { Button } from "@/shared/ui/button";
import { LoadingState } from "@/shared/ui/async-state";
import { PageIntro } from "@/shared/ui/typography";

import type { TaskDetail } from "../api/task-api";
import { TASK_GROUPS, taskCount } from "../model/task-state";
import { taskById } from "../model/task-state";
import { useTaskManagement } from "../model/use-task-management";
import { TaskFailureNotice } from "./TaskFailureNotice";
import { TaskEvidenceHistory } from "./TaskEvidenceHistory";
import { TaskForm } from "./TaskForm";
import { TaskGroup } from "./TaskGroup";
import styles from "./TaskManagement.module.css";

export function TaskManagementPanel() {
  const management = useTaskManagement();
  const loadState = management.loadState;
  const loadTaskDetail = management.detail;
  const [detail, setDetail] = useState<TaskDetail>();
  const [detailError, setDetailError] = useState<unknown>();
  const focused = useRef<number | undefined>(undefined);
  async function openDetail(taskId: number) {
    setDetailError(undefined);
    try {
      setDetail(await management.detail(taskId));
    } catch (error) {
      setDetailError(error);
    }
  }
  useEffect(() => {
    if (loadState.kind !== "ready" || typeof window === "undefined") return;
    const raw = new URLSearchParams(window.location.search).get("focus");
    const taskId = raw && /^\d+$/.test(raw) ? Number(raw) : undefined;
    if (!taskId || focused.current === taskId || !taskById(loadState.data, taskId)) return;
    focused.current = taskId;
    setDetailError(undefined);
    void loadTaskDetail(taskId).then(setDetail).catch(setDetailError);
  }, [loadState, loadTaskDetail]);
  if (management.loadState.kind === "loading") return <LoadingState />;
  if (management.loadState.kind === "failed") {
    return <LoadFailure error={management.loadState.error} onRetry={management.refresh} />;
  }
  const data = management.loadState.data;
  return (
    <section className={styles.panel}>
      <PageIntro
        title={UI_MESSAGES.tasks.title}
        description="Theo dõi tiến độ, cập nhật trạng thái và nộp minh chứng hoàn thành tại hiện trường."
      />
      <CreateTask management={management} />
      <TaskFailureNotice
        error={management.mutation.kind === "failed" ? management.mutation.error : undefined}
      />
      {management.mutation.kind === "succeeded" ? (
        <p role="status">{management.mutation.message}</p>
      ) : null}
      {management.loadState.refreshError ? (
        <p role="alert">{UI_MESSAGES.tasks.staleFailure}</p>
      ) : null}
      {taskCount(data) === 0 ? <p>{UI_MESSAGES.tasks.empty}</p> : null}
      {taskCount(data) > 0 ? (
        <TaskTabs data={data} management={management} onDetail={(id) => void openDetail(id)} />
      ) : null}
      <TaskEvidenceHistory detail={detail} error={detailError} />
    </section>
  );
}

function CreateTask({ management }: { management: ReturnType<typeof useTaskManagement> }) {
  const mode = management.capabilities.canAssign ? "assign-create" : "self-create";
  if (!management.capabilities.canAssign && !management.capabilities.canCreateSelf) return null;
  return (
    <section className={styles.createSection} aria-labelledby="create-task-title">
      <div className={styles.sectionIntro}>
        <h2 id="create-task-title">Tạo công việc</h2>
        <p>Nhập thông tin giao việc rõ ràng để nhân sự có thể bắt đầu ngay.</p>
      </div>
      <TaskForm
        mode={mode}
        users={management.users}
        locations={management.locations}
        busy={management.mutation.kind === "submitting"}
        onCreate={management.create}
      />
    </section>
  );
}

type TaskTab = "todo" | "completed" | "inProgress" | "overdue";
const TAB_LABELS: Record<TaskTab, string> = {
  todo: "Cần làm",
  completed: "Đã xong",
  inProgress: "Đang thực hiện",
  overdue: "Quá hạn",
};

function TaskTabs({
  data,
  management,
  onDetail,
}: {
  data: Parameters<typeof taskCount>[0];
  management: ReturnType<typeof useTaskManagement>;
  onDetail(id: number): void;
}) {
  const all = TASK_GROUPS.flatMap((group) => data[group]);
  const overdueIds = new Set(data.overdue.map((task) => task.id));
  const groups: Record<TaskTab, typeof all> = {
    todo: all.filter(
      (task) => !overdueIds.has(task.id) && (task.status === "TODO" || task.status === "BLOCKED"),
    ),
    completed: all.filter((task) => task.status === "COMPLETED"),
    inProgress: all.filter((task) => !overdueIds.has(task.id) && task.status === "IN_PROGRESS"),
    overdue: data.overdue.filter((task) => task.status !== "COMPLETED"),
  };
  const tabs = Object.keys(TAB_LABELS) as TaskTab[];
  const initial = tabs.find((tab) => groups[tab].length > 0) ?? "todo";
  return (
    <section className={styles.taskWorkspace} aria-labelledby="task-list-title">
      <div className={styles.sectionIntro}>
        <h2 id="task-list-title">Danh sách công việc</h2>
        <p>Chọn trạng thái để tập trung vào đúng nhóm cần xử lý.</p>
      </div>
      <Tabs.Root defaultValue={initial}>
        <Tabs.List className={styles.tabs} aria-label="Trạng thái công việc">
          {tabs.map((tab) => (
            <Tabs.Trigger key={tab} value={tab}>
              {TAB_LABELS[tab]} <span>{groups[tab].length}</span>
            </Tabs.Trigger>
          ))}
        </Tabs.List>
        {tabs.map((tab) => (
          <Tabs.Content className={styles.tabContent} key={tab} value={tab}>
            <TaskGroup
              title={TAB_LABELS[tab]}
              id={tab}
              tasks={groups[tab]}
              management={management}
              onDetail={onDetail}
            />
          </Tabs.Content>
        ))}
      </Tabs.Root>
    </section>
  );
}

function LoadFailure(props: { error: unknown; onRetry(): Promise<void> }) {
  return (
    <section>
      <p role="alert">{UI_MESSAGES.tasks.loadFailure}</p>
      <TaskFailureNotice error={props.error} />
      <Button onClick={() => void props.onRetry()}>{UI_MESSAGES.retry}</Button>
    </section>
  );
}

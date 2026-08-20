"use client";

import { useState } from "react";

import { UI_MESSAGES } from "@/shared/messages";
import { Button } from "@/shared/ui/button";
import { LoadingState } from "@/shared/ui/async-state";
import { PageIntro } from "@/shared/ui/typography";

import type { TaskDetail } from "../api/task-api";
import { TASK_GROUPS, taskCount } from "../model/task-state";
import { useTaskManagement } from "../model/use-task-management";
import { TaskFailureNotice } from "./TaskFailureNotice";
import { TaskEvidenceHistory } from "./TaskEvidenceHistory";
import { TaskForm } from "./TaskForm";
import { TaskGroup } from "./TaskGroup";
import styles from "./TaskManagement.module.css";

export function TaskManagementPanel() {
  const management = useTaskManagement();
  const [detail, setDetail] = useState<TaskDetail>();
  const [detailError, setDetailError] = useState<unknown>();
  async function openDetail(taskId: number) {
    setDetailError(undefined);
    try {
      setDetail(await management.detail(taskId));
    } catch (error) {
      setDetailError(error);
    }
  }
  if (management.loadState.kind === "loading") return <LoadingState />;
  if (management.loadState.kind === "failed") {
    return <LoadFailure error={management.loadState.error} onRetry={management.refresh} />;
  }
  const data = management.loadState.data;
  return (
    <section className={styles.panel}>
      <PageIntro eyebrow="Feature 007" title={UI_MESSAGES.tasks.title} description="Theo dõi tiến độ, cập nhật trạng thái và nộp minh chứng hoàn thành tại hiện trường." />
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
      {TASK_GROUPS.map((group) => (
        <TaskGroup
          key={group}
          group={group}
          tasks={data[group]}
          management={management}
          onDetail={(id) => void openDetail(id)}
        />
      ))}
      <TaskEvidenceHistory detail={detail} error={detailError} />
    </section>
  );
}

function CreateTask({ management }: { management: ReturnType<typeof useTaskManagement> }) {
  const mode = management.capabilities.canAssign ? "assign-create" : "self-create";
  if (!management.capabilities.canAssign && !management.capabilities.canCreateSelf) return null;
  return (
    <TaskForm
      mode={mode}
      users={management.users}
      locations={management.locations}
      busy={management.mutation.kind === "submitting"}
      onCreate={management.create}
    />
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

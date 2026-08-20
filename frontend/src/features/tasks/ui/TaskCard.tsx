"use client";

import { useState } from "react";

import { Button } from "@/shared/ui/button";
import { Card } from "@/shared/ui/card";
import type { BadgeTone } from "@/shared/ui/badge";
import { StatusBadge } from "@/shared/ui/status-badge";

import type { TaskItem } from "../api/task-api";
import type { TaskCapabilities } from "../model/task-state";
import type { useTaskManagement } from "../model/use-task-management";
import { ManagerOverrideForm } from "./ManagerOverrideForm";
import { TaskEvidenceForm } from "./TaskEvidenceForm";
import { TaskForm } from "./TaskForm";
import { TaskStatusForm } from "./TaskStatusForm";
import styles from "./TaskManagement.module.css";

type Management = ReturnType<typeof useTaskManagement>;

export function TaskCard(props: {
  task: TaskItem;
  management: Management;
  onDetail(taskId: number): void;
}) {
  const [editor, setEditor] = useState<"content" | "status" | "override" | "evidence" | "delete">();
  const busy = props.management.mutation.kind === "submitting";
  const completed = props.task.status === "COMPLETED";
  return (
    <Card aria-label={props.task.title}>
      <TaskSummary task={props.task} />
      <Button variant="quiet" onClick={() => props.onDetail(props.task.id)}>
        Xem lịch sử
      </Button>
      {!completed ? (
        <TaskActions
          capabilities={props.management.capabilities}
          task={props.task}
          accountId={props.management.accountId}
          onSelect={setEditor}
        />
      ) : null}
      {!completed ? <SelectedEditor editor={editor} busy={busy} {...props} /> : null}
    </Card>
  );
}

function SelectedEditor(props: Parameters<typeof TaskCard>[0] & { editor?: "content" | "status" | "override" | "evidence" | "delete"; busy: boolean }) {
  if (props.editor === "content") return <TaskEditor {...props} />;
  if (props.editor === "status") return (
        <TaskStatusForm
          task={props.task}
          busy={props.busy}
          onSubmit={(body) => props.management.changeStatus(props.task.id, body)}
        />
      );
  if (props.editor === "override") return (
        <ManagerOverrideForm
          taskTitle={props.task.title}
          busy={props.busy}
          onSubmit={(completion_note) =>
            props.management.override(props.task.id, { completion_note })
          }
        />
      );
  if (props.editor === "evidence") return <TaskEvidenceForm
        accountId={props.management.accountId}
        taskId={props.task.id}
        taskTitle={props.task.title}
        busy={props.busy}
        onComplete={(body, key) => props.management.completeField(props.task.id, body, key)}
      />;
  if (props.editor === "delete") return <div role="alert" className="actions">
    <span>Task sẽ được ẩn nhưng lịch sử audit vẫn được giữ lại.</span>
    <Button variant="destructive" onClick={() => props.management.remove(props.task.id)}>
      Xác nhận xóa
    </Button>
  </div>;
  return null;
}

function TaskSummary({ task }: { task: TaskItem }) {
  const status = STATUS_META[task.status];
  return (
    <header className={styles.summary}>
      <div className={styles.titleRow}><h3>{task.title}</h3><StatusBadge tone={status.tone}>{status.label}</StatusBadge></div>
      <p className={styles.description}>{task.description || "Không có mô tả."}</p>
      <dl className={styles.metadata}>
      <div><dt>Ngày giao</dt><dd>
        Ngày giao: <time dateTime={task.assigned_date}>{task.assigned_date}</time>
      </dd></div>
      {task.overdue_days ? <div><dt>Tiến độ</dt><dd><StatusBadge tone="critical">Quá hạn {task.overdue_days} ngày</StatusBadge></dd></div> : null}
      <div><dt>Người được giao</dt><dd>{task.assignees.map(({ user }) => user.full_name).join(", ")}</dd></div>
      {task.expected_location ? (
        <div><dt>Vị trí dự kiến</dt><dd>{task.expected_location}</dd></div>
      ) : null}
      </dl>
    </header>
  );
}
const STATUS_META: Record<TaskItem["status"], { label: string; tone: BadgeTone }> = {
  TODO: { label: "Cần làm", tone: "neutral" },
  IN_PROGRESS: { label: "Đang thực hiện", tone: "warning" },
  BLOCKED: { label: "Bị chặn", tone: "critical" },
  COMPLETED: { label: "Đã hoàn thành", tone: "ready" },
};

function TaskActions(props: {
  capabilities: TaskCapabilities;
  task: TaskItem;
  accountId: number;
  onSelect(value: "content" | "status" | "override" | "evidence" | "delete"): void;
}) {
  const canUpdate = props.capabilities.canUpdateAny || props.capabilities.canUpdateSelf;
  return <div className="actions">
    {canUpdate ? <UpdateActions onSelect={props.onSelect} /> : null}
    <EvidenceAction {...props} />
    <DeleteAction {...props} />
    <OverrideAction {...props} />
  </div>;
}

function EvidenceAction(props: Parameters<typeof TaskActions>[0]) {
  return props.capabilities.canCompleteField
    ? <Button variant="primary" onClick={() => props.onSelect("evidence")}>Nộp minh chứng</Button>
    : null;
}

function DeleteAction(props: Parameters<typeof TaskActions>[0]) {
  return canDeleteTask(props)
    ? <Button variant="destructive" onClick={() => props.onSelect("delete")}>Xóa task tự tạo</Button>
    : null;
}

function OverrideAction(props: Parameters<typeof TaskActions>[0]) {
  return props.capabilities.canOverride
    ? <Button variant="destructive" onClick={() => props.onSelect("override")}>Hoàn thành</Button>
    : null;
}

function canDeleteTask(props: Pick<Parameters<typeof TaskActions>[0], "capabilities" | "task" | "accountId">) {
  return props.capabilities.canDeleteSelf
    && props.task.created_by.id === props.accountId
    && props.task.assignees.length === 1
    && props.task.assignees[0]?.user.id === props.accountId;
}
function UpdateActions({ onSelect }: Pick<Parameters<typeof TaskActions>[0], "onSelect">) {
  return <><Button onClick={() => onSelect("content")}>Sửa nội dung</Button><Button onClick={() => onSelect("status")}>Đổi trạng thái</Button></>;
}

function TaskEditor(props: { task: TaskItem; management: Management; busy: boolean }) {
  return (
    <TaskForm
      mode="edit"
      task={props.task}
      users={props.management.users}
      locations={props.management.locations}
      editableAssignees={props.management.capabilities.canUpdateAny}
      busy={props.busy}
      onUpdate={(body) => props.management.update(props.task.id, body)}
    />
  );
}

"use client";

import { type FormEvent, useState } from "react";

import { UI_MESSAGES } from "@/shared/messages";
import { Button } from "@/shared/ui/button";
import { ActionGroup } from "@/shared/ui/action-group";
import { Select, Textarea } from "@/shared/ui/form";

import type { TaskItem, TaskStatusInput } from "../api/task-api";

const STATUS_LABELS = {
  TODO: "Cần làm",
  IN_PROGRESS: "Đang thực hiện",
  BLOCKED: "Bị chặn",
} as const;

const ALLOWED_TARGETS = {
  TODO: ["TODO", "IN_PROGRESS", "BLOCKED"],
  IN_PROGRESS: ["IN_PROGRESS", "BLOCKED"],
  BLOCKED: ["BLOCKED", "IN_PROGRESS"],
} as const;

export function TaskStatusForm(props: {
  task: TaskItem;
  busy: boolean;
  onSubmit(body: TaskStatusInput): Promise<void>;
}) {
  const [target, setTarget] = useState<keyof typeof STATUS_LABELS>(
    props.task.status === "COMPLETED" ? "TODO" : props.task.status,
  );
  const [reasonError, setReasonError] = useState(false);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const block_reason = String(data.get("block_reason") ?? "").trim();
    if (target === "BLOCKED" && !block_reason && props.task.status !== "BLOCKED") {
      setReasonError(true);
      return;
    }
    setReasonError(false);
    await props.onSubmit({
      status: target,
      note: String(data.get("note") ?? "").trim() || null,
      block_reason: block_reason || null,
    });
  }
  return (
    <form onSubmit={submit} aria-label={`Cập nhật trạng thái ${props.task.title}`}>
      <label>
        Trạng thái
        <Select
          name="status"
          value={target}
          onChange={(event) => setTarget(event.target.value as keyof typeof STATUS_LABELS)}
        >
          {ALLOWED_TARGETS[props.task.status === "COMPLETED" ? "TODO" : props.task.status].map(
            (value) => (
              <option key={value} value={value}>
                {STATUS_LABELS[value]}
              </option>
            ),
          )}
        </Select>
      </label>
      <label>
        Ghi chú
        <Textarea name="note" />
      </label>
      {target === "BLOCKED" ? (
        <label>
          Lý do bị chặn
          <Textarea name="block_reason" />
        </label>
      ) : null}
      {reasonError ? <p role="alert">{UI_MESSAGES.tasks.blockedReason}</p> : null}
      <ActionGroup>
        <Button type="submit" loading={props.busy}>
          Cập nhật trạng thái
        </Button>
      </ActionGroup>
    </form>
  );
}

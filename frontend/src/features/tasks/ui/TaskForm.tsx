"use client";

import { type FormEvent, useId, useRef, useState } from "react";

import type { listUsers } from "@/features/identity/api/identity-api";
import type { listLocations } from "@/features/locations/api/location-api";
import { UI_MESSAGES } from "@/shared/messages";
import { Button } from "@/shared/ui/button";
import { ActionGroup } from "@/shared/ui/action-group";
import { Input, Textarea } from "@/shared/ui/form";

import type { TaskCreateInput, TaskItem, TaskUpdateInput } from "../api/task-api";
import styles from "./TaskManagement.module.css";

type User = Awaited<ReturnType<typeof listUsers>>["results"][number];
type Location = Awaited<ReturnType<typeof listLocations>>[number];

type TaskFormProps = {
  mode: "self-create" | "assign-create" | "edit";
  users: readonly User[];
  locations: readonly Location[];
  busy: boolean;
  task?: TaskItem;
  editableAssignees?: boolean;
  onCreate?(body: TaskCreateInput): Promise<void>;
  onUpdate?(body: TaskUpdateInput): Promise<void>;
};

function selectedNumbers(data: FormData, name: string): number[] {
  return data.getAll(name).map((value) => Number(value));
}

function taskContent(data: FormData) {
  return {
    title: String(data.get("title") ?? "").trim(),
    description: String(data.get("description") ?? "").trim(),
    expected_location: String(data.get("expected_location") ?? "").trim(),
  };
}

function desiredAssignees(data: FormData, task: TaskItem): number[] {
  const removed = new Set(selectedNumbers(data, "remove_assignee_id"));
  const retained = task.assignees.map(({ user }) => user.id).filter((id) => !removed.has(id));
  return [...new Set([...retained, ...selectedNumbers(data, "assignee_ids")])];
}

export function TaskForm(props: TaskFormProps) {
  const [clientError, setClientError] = useState<string>();
  const locationListId = useId();
  const submitting = useRef(false);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (props.busy || submitting.current) return;
    submitting.current = true;
    const form = event.currentTarget;
    const data = new FormData(form);
    setClientError(undefined);
    try {
      const created = await submitTaskForm(props, data, setClientError);
      if (created) form.reset();
    } catch {
      setClientError(UI_MESSAGES.tasks.mutationFailure);
    } finally {
      submitting.current = false;
    }
  }

  return (
    <form
      className={props.mode === "edit" ? styles.editForm : styles.createForm}
      onSubmit={submit}
      aria-label={props.mode === "edit" ? "Sửa công việc" : "Tạo công việc"}
    >
      <TaskContentFields
        task={props.task}
        locations={props.locations}
        creating={!props.task}
        locationListId={locationListId}
      />
      {props.mode === "assign-create" || props.editableAssignees ? (
        <AssignmentFields {...props} />
      ) : null}
      {clientError ? <p role="alert">{clientError}</p> : null}
      <ActionGroup>
        <Button type="submit" variant="primary" loading={props.busy}>
          {props.mode === "edit" ? UI_MESSAGES.tasks.save : UI_MESSAGES.tasks.create}
        </Button>
      </ActionGroup>
    </form>
  );
}

async function submitTaskForm(
  props: TaskFormProps,
  data: FormData,
  setError: (value: string) => void,
) {
  if (props.mode === "edit") {
    await submitEdit(props, data, setError);
    return false;
  }
  return await submitCreate(props, data, setError);
}

async function submitEdit(props: TaskFormProps, data: FormData, setError: (value: string) => void) {
  if (!props.task || !props.onUpdate) return;
  if (!props.editableAssignees) return await props.onUpdate(taskContent(data));
  const assignee_ids = desiredAssignees(data, props.task);
  if (assignee_ids.length === 0) return setError("Cần ít nhất một người được giao.");
  return await props.onUpdate({ ...taskContent(data), assignee_ids });
}

async function submitCreate(
  props: TaskFormProps,
  data: FormData,
  setError: (value: string) => void,
) {
  if (!props.onCreate) return false;
  const assignee_ids = selectedNumbers(data, "assignee_ids");
  if (props.mode === "assign-create" && assignee_ids.length === 0) {
    setError("Cần chọn ít nhất một nhân viên Helpdesk.");
    return false;
  }
  const body = { ...taskContent(data), assigned_date: String(data.get("assigned_date")) };
  await props.onCreate(props.mode === "assign-create" ? { ...body, assignee_ids } : body);
  return true;
}

function TaskContentFields(props: {
  task?: TaskItem;
  locations: readonly Location[];
  creating: boolean;
  locationListId: string;
}) {
  return (
    <div className={styles.taskFormGrid}>
      <label>
        Tiêu đề
        <Input name="title" required defaultValue={props.task?.title} />
      </label>
      <label>
        Mô tả
        <Textarea
          className={styles.descriptionInput}
          name="description"
          defaultValue={props.task?.description}
        />
      </label>
      {props.creating ? (
        <label>
          Ngày giao
          <Input name="assigned_date" type="date" required />
        </label>
      ) : null}
      <label>
        {UI_MESSAGES.tasks.expectedLocation}
        <Input
          name="expected_location"
          list={props.locationListId}
          maxLength={500}
          placeholder="Ví dụ: UBND phường 1, Trường THCS Nguyễn Du"
          defaultValue={props.task?.expected_location ?? ""}
        />
        <datalist id={props.locationListId}>
          {props.locations.map((location) => (
            <option key={location.id} value={`${location.code} — ${location.name}`} />
          ))}
        </datalist>
      </label>
    </div>
  );
}

function AssignmentFields(props: TaskFormProps) {
  const headingId = useId();
  return (
    <div className={styles.assignmentBlock}>
      <div className={styles.assignmentHeading}>
        <div>
          <h3 id={headingId}>{UI_MESSAGES.tasks.activeAssignees}</h3>
          <p>Chọn một hoặc nhiều người phụ trách công việc.</p>
        </div>
        <span>{props.users.length} người</span>
      </div>
      <div
        className={styles.assigneeList}
        role="group"
        aria-labelledby={headingId}
        aria-label={UI_MESSAGES.tasks.activeAssignees}
      >
        {props.users.length ? (
          props.users.map((user) => (
            <label className={styles.assigneeOption} key={user.id}>
              <Input type="checkbox" name="assignee_ids" value={user.id} />
              <span>
                <strong>{user.full_name}</strong>
                <small>@{user.username}</small>
              </span>
            </label>
          ))
        ) : (
          <p className={styles.emptyAssignees}>Không có Helpdesk đang hoạt động.</p>
        )}
      </div>
      {props.mode === "edit" && props.task ? <RetainedAssignees task={props.task} /> : null}
    </div>
  );
}

function RetainedAssignees({ task }: { task: TaskItem }) {
  return (
    <fieldset>
      <legend>{UI_MESSAGES.tasks.retainedAssignees}</legend>
      {task.assignees.map(({ user }) => (
        <label className="checkbox" key={user.id}>
          <Input
            className="mt-0 min-h-5 w-5 shadow-none"
            type="checkbox"
            name="remove_assignee_id"
            value={user.id}
          />
          Bỏ {user.full_name}
        </label>
      ))}
    </fieldset>
  );
}

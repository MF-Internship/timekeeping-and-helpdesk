"use client";

import { type FormEvent, useState } from "react";

import { UI_MESSAGES } from "@/shared/messages";
import { Button } from "@/shared/ui/button";
import { ActionGroup } from "@/shared/ui/action-group";
import { Input, Textarea } from "@/shared/ui/form";

export function ManagerOverrideForm(props: {
  taskTitle: string;
  busy: boolean;
  onSubmit(note: string): Promise<void>;
}) {
  const [confirmed, setConfirmed] = useState(false);
  const [error, setError] = useState(false);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const note = String(new FormData(event.currentTarget).get("completion_note") ?? "").trim();
    if (!confirmed || !note) {
      setError(true);
      return;
    }
    setError(false);
    await props.onSubmit(note);
  }
  return (
    <form onSubmit={submit} aria-label={`Hoàn thành ${props.taskTitle}`}>
      <label>
        Ghi chú hoàn thành
        <Textarea name="completion_note" required />
      </label>
      <label className="checkbox">
        <Input className="mt-0 min-h-5 w-5 shadow-none"
          type="checkbox"
          checked={confirmed}
          onChange={(event) => setConfirmed(event.target.checked)}
        />
        Xác nhận hoàn thành vĩnh viễn
      </label>
      {error ? <p role="alert">{UI_MESSAGES.tasks.completionNote}</p> : null}
      <ActionGroup><Button type="submit" variant="destructive" loading={props.busy}>
        Hoàn thành
      </Button></ActionGroup>
    </form>
  );
}

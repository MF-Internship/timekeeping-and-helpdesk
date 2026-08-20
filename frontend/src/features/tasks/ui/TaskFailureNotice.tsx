import type { ApiFailure } from "@/shared/errors/api-error";
import { UI_MESSAGES } from "@/shared/messages";

function isApiFailure(error: unknown): error is ApiFailure {
  return typeof error === "object" && error !== null && "kind" in error;
}

export function TaskFailureNotice({ error }: { error?: unknown }) {
  if (!error) return null;
  if (!isApiFailure(error)) return <p role="alert">{UI_MESSAGES.tasks.mutationFailure}</p>;
  if (error.kind === "canonical") {
    const ids = error.details.assignee_ids;
    const message =
      error.errorCode === "TASK_ALREADY_COMPLETED" ? UI_MESSAGES.tasks.conflict : error.message;
    return (
      <div role="alert">
        <p>{message}</p>
        {Array.isArray(ids) && ids.every((id) => typeof id === "number") ? (
          <p>ID không hợp lệ: {ids.join(", ")}</p>
        ) : null}
        <p>Mã hỗ trợ: {error.requestId}</p>
      </div>
    );
  }
  return <p role="alert">{UI_MESSAGES.tasks.mutationFailure}</p>;
}

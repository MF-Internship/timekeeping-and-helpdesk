import { UI_MESSAGES } from "@/shared/messages";
import { Button } from "@/shared/ui/button";
import { Card } from "@/shared/ui/card";

export type AsyncStateValue =
  | { kind: "loading" }
  | { kind: "empty" }
  | {
      kind: "canonical";
      message: string;
      details: Record<string, unknown>;
      requestId: string;
    }
  | { kind: "unexpected_response" }
  | { kind: "network" };

export interface AsyncStateProps {
  state: AsyncStateValue;
  onRetry?: () => void;
}

export function LoadingState({ message = UI_MESSAGES.loading }: { message?: string }) {
  return (
    <p role="status" aria-live="polite" aria-busy="true">
      {message}
    </p>
  );
}

export function EmptyState({ message = UI_MESSAGES.empty }: { message?: string }) {
  return <p role="status">{message}</p>;
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <Card role="alert">
      <p>{message}</p>
      {onRetry && <Button onClick={onRetry}>{UI_MESSAGES.retry}</Button>}
    </Card>
  );
}

export function AsyncState({ state, onRetry }: AsyncStateProps) {
  if (state.kind === "loading") return <LoadingState />;
  if (state.kind === "empty") return <EmptyState />;

  const message = failureMessage(state);
  return (
    <section role="alert">
      <p>{message}</p>
      {state.kind === "canonical" ? (
        <>
          {Object.entries(state.details).map(([field, value]) => (
            <p key={field}>{safeDetail(value)}</p>
          ))}
          <p>Mã hỗ trợ: {state.requestId}</p>
        </>
      ) : null}
      {onRetry ? <Button onClick={onRetry}>{UI_MESSAGES.retry}</Button> : null}
    </section>
  );
}

function failureMessage(state: Exclude<AsyncStateValue, { kind: "loading" | "empty" }>): string {
  if (state.kind === "canonical") return state.message;
  if (state.kind === "network") return UI_MESSAGES.networkFailure;
  return UI_MESSAGES.unexpectedResponse;
}

function safeDetail(value: unknown): string {
  if (Array.isArray(value) && value.every((item) => typeof item === "string")) {
    return value.join(" ");
  }
  return UI_MESSAGES.unexpectedResponse;
}

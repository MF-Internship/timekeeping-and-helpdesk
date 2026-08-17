import { UI_MESSAGES } from "@/shared/messages";

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

export function AsyncState({ state, onRetry }: AsyncStateProps) {
  if (state.kind === "loading") return <p role="status">{UI_MESSAGES.loading}</p>;
  if (state.kind === "empty") return <p role="status">{UI_MESSAGES.empty}</p>;

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
      {onRetry ? <button onClick={onRetry}>{UI_MESSAGES.retry}</button> : null}
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

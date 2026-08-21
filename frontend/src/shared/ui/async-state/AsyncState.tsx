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
    <div role="status" aria-live="polite" aria-busy="true" className="state-panel">
      <span className="state-spinner" aria-hidden="true" />
      {message}
    </div>
  );
}

export function EmptyState({ message = UI_MESSAGES.empty }: { message?: string }) {
  return (
    <div className="state-panel" role="status">
      <strong>Chưa có dữ liệu</strong>
      <span>{message}</span>
    </div>
  );
}

export function PermissionState({ message = UI_MESSAGES.permissionDenied }: { message?: string }) {
  return (
    <div className="state-panel" role="alert">
      <strong>Không thể truy cập</strong>
      <span>{message}</span>
    </div>
  );
}

export function SkeletonState({ rows = 3 }: { rows?: number }) {
  return (
    <div className="skeleton-stack" role="status" aria-label={UI_MESSAGES.loading}>
      {Array.from({ length: rows }, (_, index) => (
        <span key={index} className="skeleton-row" />
      ))}
    </div>
  );
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
          {Object.entries(state.details).map(([field, value]) => {
            const detail = safeDetail(value);
            return detail ? <p key={field}>{detail}</p> : null;
          })}
          <details>
            <summary>Thông tin hỗ trợ</summary>
            <p>Mã yêu cầu: {state.requestId}</p>
          </details>
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

function safeDetail(value: unknown): string | undefined {
  if (Array.isArray(value) && value.every((item) => typeof item === "string")) {
    return value.join(" ");
  }
  return undefined;
}

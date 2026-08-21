import type { ApiFailure } from "@/shared/errors/api-error";
import { UI_MESSAGES } from "@/shared/messages";

export type IdentityFailureView = {
  message: string;
  requestId?: string;
  fields: Record<string, string>;
};

const canonicalMessages: Record<string, string> = {
  INVALID_CREDENTIALS: UI_MESSAGES.invalidCredentials,
  INVALID_TOKEN: UI_MESSAGES.invalidToken,
  ACCOUNT_INACTIVE: UI_MESSAGES.accountInactive,
  PASSWORD_CHANGE_REQUIRED: UI_MESSAGES.passwordChangeRequired,
  PERMISSION_DENIED: UI_MESSAGES.permissionDenied,
  SERVER_OWNED_FIELD: UI_MESSAGES.serverOwnedField,
  VALIDATION_FAILED: UI_MESSAGES.validationFailed,
  THROTTLED: UI_MESSAGES.throttled,
  SERVICE_UNAVAILABLE: UI_MESSAGES.serviceUnavailable,
};

export function identityFailureView(error: unknown): IdentityFailureView {
  if (!isApiFailure(error)) return { message: UI_MESSAGES.unexpectedResponse, fields: {} };
  if (error.kind === "network") return { message: UI_MESSAGES.networkFailure, fields: {} };
  if (error.kind === "unexpected_response") {
    return {
      message: UI_MESSAGES.unexpectedResponse,
      fields: {},
      ...(error.requestId ? { requestId: error.requestId } : {}),
    };
  }
  const baseMessage = canonicalMessages[error.errorCode] ?? UI_MESSAGES.unexpectedResponse;
  const message =
    error.errorCode === "THROTTLED" && error.retryAfterSeconds
      ? `${baseMessage} ${error.retryAfterSeconds} giây.`
      : baseMessage;
  return {
    message,
    fields: detailMessages(error.details),
    requestId: error.requestId,
  };
}

export function IdentityFailureNotice({ failure }: { failure?: IdentityFailureView }) {
  if (!failure) return null;
  return (
    <div role="alert">
      <p>{failure.message}</p>
      {failure.requestId ? (
        <details>
          <summary>Thông tin hỗ trợ</summary>
          <small>Mã yêu cầu: {failure.requestId}</small>
        </details>
      ) : null}
    </div>
  );
}

function detailMessages(details: Record<string, unknown>): Record<string, string> {
  return Object.fromEntries(
    Object.entries(details).flatMap(([field, value]) => {
      const message = Array.isArray(value) ? value.find((item) => typeof item === "string") : value;
      return typeof message === "string" ? [[field, message]] : [];
    }),
  );
}

function isApiFailure(error: unknown): error is ApiFailure {
  if (typeof error !== "object" || error === null || !("kind" in error)) return false;
  return ["canonical", "unexpected_response", "network"].includes(
    String((error as { kind: unknown }).kind),
  );
}

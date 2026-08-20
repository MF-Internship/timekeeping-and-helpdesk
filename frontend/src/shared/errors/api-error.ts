const requestIdPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;
const authorizedCodes = new Set([
  "VALIDATION_FAILED",
  "PERMISSION_DENIED",
  "INVALID_CREDENTIALS",
  "INVALID_TOKEN",
  "ACCOUNT_INACTIVE",
  "PASSWORD_CHANGE_REQUIRED",
  "SERVER_OWNED_FIELD",
  "NOT_FOUND",
  "LOCATION_VERSION_CONFLICT",
  "THROTTLED",
  "SERVICE_UNAVAILABLE",
  "WEAK_GPS",
  "OUTSIDE_RADIUS",
  "LOCATION_CHOICE_REQUIRED",
  "INVALID_LOCATION_CHOICE",
  "NO_OPEN_SESSION",
  "SESSION_ALREADY_OPEN",
  "INACTIVE_ASSIGNEE",
  "BLOCK_REASON_REQUIRED",
  "TASK_ALREADY_COMPLETED",
  "EVIDENCE_UPLOAD_INVALID",
  "EVIDENCE_UPLOAD_NOT_READY",
  "IDEMPOTENCY_CONFLICT",
]);

export type ApiFailure =
  | {
      kind: "canonical";
      errorCode: string;
      message: string;
      details: Record<string, unknown>;
      requestId: string;
      retryAfterSeconds?: number;
    }
  | { kind: "unexpected_response"; status: number; requestId?: string }
  | { kind: "network" };

export function networkFailure(): ApiFailure {
  return { kind: "network" };
}

export async function parseApiFailure(response: Response): Promise<ApiFailure> {
  const headerRequestId = validRequestId(response.headers.get("X-Request-Id"));
  const body = await readJson(response);
  if (!isCanonicalBody(body)) return unexpectedFailure(response.status, headerRequestId);
  const bodyRequestId = validRequestId(body.request_id);
  if (bodyRequestId === undefined || (headerRequestId && headerRequestId !== bodyRequestId)) {
    return unexpectedFailure(response.status, headerRequestId);
  }
  if (!mirrorsMatch(body, body.details)) return unexpectedFailure(response.status, headerRequestId);
  const retryAfter = retryAfterSeconds(response.headers.get("Retry-After"));
  return {
    kind: "canonical",
    errorCode: body.error_code,
    message: body.message,
    details: body.details,
    requestId: bodyRequestId,
    ...(retryAfter === undefined ? {} : { retryAfterSeconds: retryAfter }),
  };
}

function retryAfterSeconds(value: string | null): number | undefined {
  if (value === null || !/^\d+$/.test(value)) return undefined;
  const seconds = Number(value);
  return Number.isSafeInteger(seconds) && seconds > 0 ? seconds : undefined;
}

export async function parseApiResultFailure(result: {
  error?: unknown;
  response: Response;
}): Promise<ApiFailure> {
  if (result.error === undefined) return await parseApiFailure(result.response);
  const response = new Response(JSON.stringify(result.error), {
    status: result.response.status,
    statusText: result.response.statusText,
    headers: result.response.headers,
  });
  return await parseApiFailure(response);
}

async function readJson(response: Response): Promise<unknown> {
  try {
    return await response.json();
  } catch {
    return undefined;
  }
}

function isCanonicalBody(body: unknown): body is Record<string, unknown> & {
  error_code: string;
  message: string;
  details: Record<string, unknown>;
} {
  if (!isRecord(body) || !isRecord(body.details)) return false;
  if (typeof body.error_code !== "string" || !authorizedCodes.has(body.error_code)) return false;
  return body.error === body.error_code && typeof body.message === "string";
}

function unexpectedFailure(status: number, requestId?: string): ApiFailure {
  return {
    kind: "unexpected_response",
    status,
    ...(requestId === undefined ? {} : { requestId }),
  };
}

function mirrorsMatch(body: Record<string, unknown>, details: Record<string, unknown>): boolean {
  return Object.entries(details).every(([key, value]) => {
    if (["error_code", "message", "details", "request_id", "error"].includes(key)) return true;
    return JSON.stringify(body[key]) === JSON.stringify(value);
  });
}

function validRequestId(value: unknown): string | undefined {
  return typeof value === "string" && requestIdPattern.test(value) ? value : undefined;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

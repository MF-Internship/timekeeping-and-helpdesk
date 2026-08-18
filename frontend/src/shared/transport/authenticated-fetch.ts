let accessToken: string | undefined;
let sessionGeneration = 0;
let refreshFlight: { generation: number; promise: Promise<boolean> } | undefined;
let authenticationFailureHandler: ((code: string) => void) | undefined;
const STATUS_UNAUTHORIZED = 401;

export function setMemoryAccessToken(value: string | undefined): void {
  accessToken = value;
  sessionGeneration += 1;
}

export function clearMemoryAccessToken(): void {
  accessToken = undefined;
  sessionGeneration += 1;
}

export function setAuthenticationFailureHandler(
  handler: ((code: string) => void) | undefined,
): void {
  authenticationFailureHandler = handler;
}

export async function authenticatedFetch(
  input: RequestInfo | URL,
  init: RequestInit = {},
): Promise<Response> {
  const target = apiTarget(input);
  if (!target) {
    throw new TypeError("API target must be a relative /api/v1/ path");
  }
  const response = await fetch(fetchInput(input), requestOptions(input, init));
  const errorCode = await responseErrorCode(response);
  if (handleAuthenticationFailure(errorCode)) return response;
  if (!shouldRefresh(target, response, errorCode)) return response;
  if (!(await refreshOnce())) return response;
  return fetch(fetchInput(input), requestOptions(input, init));
}

function handleAuthenticationFailure(errorCode: string | undefined): boolean {
  if (errorCode === "ACCOUNT_INACTIVE") {
    clearMemoryAccessToken();
    authenticationFailureHandler?.(errorCode);
    return true;
  }
  if (errorCode === "PASSWORD_CHANGE_REQUIRED") {
    authenticationFailureHandler?.(errorCode);
    return true;
  }
  return false;
}

function requestOptions(input: RequestInfo | URL, init: RequestInit): RequestInit {
  const headers = new Headers(input instanceof Request ? input.headers : undefined);
  new Headers(init.headers).forEach((value, key) => headers.set(key, value));
  if (!headers.has("Accept")) headers.set("Accept", "application/json");
  if (accessToken && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${accessToken}`);
  }
  return {
    ...init,
    headers,
    credentials: "include",
    cache: "no-store",
  };
}

function apiTarget(input: RequestInfo | URL): string | undefined {
  if (typeof input === "string") return isApiTarget(input) ? input : undefined;
  if (!(input instanceof Request) || globalThis.location === undefined) return undefined;
  const url = new URL(input.url);
  if (url.origin !== globalThis.location.origin) return undefined;
  const target = `${url.pathname}${url.search}`;
  return isApiTarget(target) ? target : undefined;
}

function fetchInput(input: RequestInfo | URL): RequestInfo | URL {
  return input instanceof Request ? input.clone() : input;
}

function isApiTarget(target: string): boolean {
  return target.startsWith("/api/v1/") && !target.startsWith("//");
}

function shouldRefresh(target: string, response: Response, errorCode: string | undefined): boolean {
  if (
    !accessToken ||
    response.status !== STATUS_UNAUTHORIZED ||
    target.startsWith("/api/v1/auth/")
  ) {
    return false;
  }
  return errorCode === "INVALID_TOKEN";
}

async function responseErrorCode(response: Response): Promise<string | undefined> {
  if (response.ok) return undefined;
  try {
    const payload = (await response.clone().json()) as { error_code?: unknown };
    return typeof payload.error_code === "string" ? payload.error_code : undefined;
  } catch {
    return undefined;
  }
}

function refreshOnce(): Promise<boolean> {
  if (refreshFlight?.generation === sessionGeneration) return refreshFlight.promise;
  const generation = sessionGeneration;
  const promise = performRefresh(generation).finally(() => {
    if (refreshFlight?.promise === promise) refreshFlight = undefined;
  });
  refreshFlight = { generation, promise };
  return promise;
}

async function performRefresh(generation: number): Promise<boolean> {
  const response = await fetch("/api/v1/auth/refresh", {
    method: "POST",
    headers: { Accept: "application/json", "Content-Type": "application/json" },
    body: "{}",
    credentials: "include",
    cache: "no-store",
  });
  if (!response.ok) {
    if (sessionGeneration !== generation) return true;
    clearMemoryAccessToken();
    authenticationFailureHandler?.("INVALID_TOKEN");
    return false;
  }
  const payload = (await response.json()) as { access?: unknown };
  if (typeof payload.access !== "string") {
    if (sessionGeneration !== generation) return true;
    clearMemoryAccessToken();
    authenticationFailureHandler?.("INVALID_TOKEN");
    return false;
  }
  if (sessionGeneration !== generation) return true;
  setMemoryAccessToken(payload.access);
  return true;
}

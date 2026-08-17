export async function authenticatedFetch(
  input: RequestInfo | URL,
  init: RequestInit = {},
): Promise<Response> {
  if (typeof input !== "string" || !isApiTarget(input)) {
    throw new TypeError("API target must be a relative /api/v1/ path");
  }
  const headers = new Headers(init.headers);
  if (!headers.has("Accept")) headers.set("Accept", "application/json");
  return fetch(input, {
    ...init,
    headers,
    credentials: "include",
    cache: "no-store",
  });
}

function isApiTarget(target: string): boolean {
  return target.startsWith("/api/v1/") && !target.startsWith("//");
}

type CacheEnvelope<T> = {
  accountId: number;
  savedAt: number;
  value: T;
};

const PREFIX = "mbf-user-resource";
const DEFAULT_MAX_AGE_MS = 300_000;

function cacheKey(accountId: number, resource: string) {
  return `${PREFIX}:${accountId}:${resource}`;
}

export function readUserCache<T>(
  accountId: number | undefined,
  resource: string,
  maxAgeMs = DEFAULT_MAX_AGE_MS,
): T | undefined {
  if (accountId === undefined || typeof window === "undefined") return undefined;
  try {
    const raw = window.sessionStorage.getItem(cacheKey(accountId, resource));
    if (!raw) return undefined;
    const cached = JSON.parse(raw) as CacheEnvelope<T>;
    if (cached.accountId !== accountId || Date.now() - cached.savedAt > maxAgeMs) {
      window.sessionStorage.removeItem(cacheKey(accountId, resource));
      return undefined;
    }
    return cached.value;
  } catch {
    return undefined;
  }
}

export function writeUserCache<T>(accountId: number | undefined, resource: string, value: T) {
  if (accountId === undefined || typeof window === "undefined") return;
  try {
    const envelope: CacheEnvelope<T> = { accountId, savedAt: Date.now(), value };
    window.sessionStorage.setItem(cacheKey(accountId, resource), JSON.stringify(envelope));
  } catch {
    // Storage can be unavailable or full; network data remains the source of truth.
  }
}

export function clearUserCache(accountId: number | undefined, resourcePrefix: string) {
  if (accountId === undefined || typeof window === "undefined") return;
  const prefix = cacheKey(accountId, resourcePrefix);
  try {
    for (let index = window.sessionStorage.length - 1; index >= 0; index -= 1) {
      const key = window.sessionStorage.key(index);
      if (key?.startsWith(prefix)) window.sessionStorage.removeItem(key);
    }
  } catch {
    // Cache invalidation is best effort.
  }
}

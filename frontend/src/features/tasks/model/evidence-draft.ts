export type EvidenceDraft = {
  photos: EvidenceDraftPhoto[];
  note: string;
  expiresAt: number;
};

type EvidenceDraftPhoto = {
  name: string;
  mime: string;
  lastModified: number;
  base64: string;
};

export type DraftLoadResult =
  | { kind: "ready"; files: File[]; note: string }
  | { kind: "empty" | "expired" | "evicted" | "invalid" | "unavailable" };

export type DraftSaveResult = { kind: "saved" } | { kind: "quota" | "unavailable" };

const PREFIX = "task-evidence-draft:";
const MARKER_PREFIX = "task-evidence-draft-marker:";
const RETENTION_MS = 7 * 24 * 60 * 60 * 1000;

function key(accountId: number, taskId: number) {
  return `${PREFIX}${accountId}:${taskId}`;
}

function markerKey(accountId: number, taskId: number) {
  return `${MARKER_PREFIX}${accountId}:${taskId}`;
}

// eslint-disable-next-line complexity
export function loadEvidenceDraft(accountId: number, taskId: number): DraftLoadResult {
  if (accountId <= 0) return { kind: "unavailable" };
  try {
    const storageKey = key(accountId, taskId);
    const raw = localStorage.getItem(storageKey);
    if (!raw) {
      return sessionStorage.getItem(markerKey(accountId, taskId))
        ? { kind: "evicted" }
        : { kind: "empty" };
    }
    const value = JSON.parse(raw) as Partial<EvidenceDraft>;
    if (typeof value.expiresAt !== "number" || value.expiresAt <= Date.now()) {
      clearEvidenceDraft(accountId, taskId);
      return { kind: "expired" };
    }
    if (!validPhotos(value.photos) || typeof value.note !== "string") {
      clearEvidenceDraft(accountId, taskId);
      return { kind: "invalid" };
    }
    return { kind: "ready", files: value.photos.map(asFile), note: value.note };
  } catch {
    return { kind: "unavailable" };
  }
}

export async function saveEvidenceDraft(
  accountId: number,
  taskId: number,
  files: readonly File[],
  note: string,
): Promise<DraftSaveResult> {
  if (accountId <= 0) return { kind: "unavailable" };
  if (!files.length && !note.trim()) {
    clearEvidenceDraft(accountId, taskId);
    return { kind: "saved" };
  }
  try {
    const photos = await Promise.all(files.map(asDraftPhoto));
    localStorage.setItem(
      key(accountId, taskId),
      JSON.stringify({ photos, note, expiresAt: Date.now() + RETENTION_MS } satisfies EvidenceDraft),
    );
    sessionStorage.setItem(markerKey(accountId, taskId), "1");
    return { kind: "saved" };
  } catch (error) {
    return isQuotaError(error) ? { kind: "quota" } : { kind: "unavailable" };
  }
}

export function clearEvidenceDraft(accountId: number, taskId: number) {
  try {
    localStorage.removeItem(key(accountId, taskId));
    sessionStorage.removeItem(markerKey(accountId, taskId));
  } catch {
    // Storage may be blocked; the UI reports that state on its next operation.
  }
}

export function purgeEvidenceDrafts(accountId?: number) {
  try {
    const prefix = accountId === undefined ? PREFIX : `${PREFIX}${accountId}:`;
    const markerPrefix = accountId === undefined ? MARKER_PREFIX : `${MARKER_PREFIX}${accountId}:`;
    removeMatching(localStorage, prefix);
    removeMatching(sessionStorage, markerPrefix);
  } catch {
    // Best-effort purge when browser storage is unavailable.
  }
}

function removeMatching(storage: Storage, prefix: string) {
  const keys = Array.from({ length: storage.length }, (_, index) => storage.key(index));
  keys.forEach((value) => {
    if (value?.startsWith(prefix)) storage.removeItem(value);
  });
}

function validPhotos(value: unknown): value is EvidenceDraftPhoto[] {
  return Array.isArray(value) && value.length <= 5 && value.every((photo) =>
    typeof photo === "object" && photo !== null
    && typeof (photo as EvidenceDraftPhoto).name === "string"
    && typeof (photo as EvidenceDraftPhoto).mime === "string"
    && typeof (photo as EvidenceDraftPhoto).lastModified === "number"
    && typeof (photo as EvidenceDraftPhoto).base64 === "string"
  );
}

async function asDraftPhoto(file: File): Promise<EvidenceDraftPhoto> {
  const bytes = new Uint8Array(await new Response(file).arrayBuffer());
  let binary = "";
  bytes.forEach((value) => { binary += String.fromCharCode(value); });
  return { name: file.name, mime: file.type, lastModified: file.lastModified, base64: btoa(binary) };
}

function asFile(photo: EvidenceDraftPhoto): File {
  const binary = atob(photo.base64);
  const bytes = Uint8Array.from(binary, (value) => value.charCodeAt(0));
  return new File([bytes], photo.name, { type: photo.mime, lastModified: photo.lastModified });
}

function isQuotaError(error: unknown) {
  return error instanceof DOMException
    && (error.name === "QuotaExceededError" || error.name === "NS_ERROR_DOM_QUOTA_REACHED");
}

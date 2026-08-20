"use client";

import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type Dispatch,
  type MutableRefObject,
  type SetStateAction,
} from "react";

import type {
  AcquisitionErrorKind,
  AcquisitionPermission,
  AcquisitionState,
  GuidancePosition,
} from "./position-types";

/** Single-shot acquisition: the watch is torn down the instant one sample arrives. */
export const ACQUISITION_TIMEOUT_MS = 15000;

const ACQUISITION_OPTIONS: PositionOptions = {
  enableHighAccuracy: true,
  maximumAge: 0,
  timeout: ACQUISITION_TIMEOUT_MS,
};

// GeolocationPositionError codes, spelled out because the interface is not a
// runtime global in every environment.
const PERMISSION_DENIED_CODE = 1;
const POSITION_UNAVAILABLE_CODE = 2;
const TIMEOUT_CODE = 3;

/**
 * Maps a browser acquisition failure onto the closed four-value vocabulary.
 * There is deliberately no fallthrough to an Attendance server error code: a
 * browser `TIMEOUT` is never presented as `WEAK_GPS` (FR-008a, FR-008b).
 */
export function classifyAcquisitionError(failure: unknown): AcquisitionErrorKind {
  if (typeof failure !== "object" || failure === null || !("code" in failure)) {
    return "UNKNOWN";
  }
  const code = (failure as { code: unknown }).code;
  if (code === PERMISSION_DENIED_CODE) return "PERMISSION_DENIED";
  if (code === POSITION_UNAVAILABLE_CODE) return "UNAVAILABLE";
  if (code === TIMEOUT_CODE) return "TIMEOUT";
  return "UNKNOWN";
}

const LATITUDE_BOUND_DEG = 90;
const LONGITUDE_BOUND_DEG = 180;

function withinRange(value: number, bound: number): boolean {
  return Number.isFinite(value) && value >= -bound && value <= bound;
}

/**
 * Validates a device sample before any distance is computed. An unusable sample
 * never reaches the geometry (FR-009). `accuracyM` is carried verbatim, with no
 * rescaling or reinterpretation (FR-003b), and `capturedAt` comes from the
 * device sample timestamp, never from a server clock (FR-005).
 */
export function readGuidanceSample(sample: GeolocationPosition): GuidancePosition | undefined {
  const { latitude, longitude, accuracy } = sample.coords;
  if (!withinRange(latitude, LATITUDE_BOUND_DEG)) return undefined;
  if (!withinRange(longitude, LONGITUDE_BOUND_DEG)) return undefined;
  if (!Number.isFinite(accuracy) || accuracy < 0) return undefined;
  return {
    latitude,
    longitude,
    accuracyM: accuracy,
    capturedAt: new Date(sample.timestamp).toISOString(),
  };
}

async function probePermission(): Promise<PermissionStatus | undefined> {
  const permissions = globalThis.navigator?.permissions;
  if (!permissions?.query) return undefined;
  try {
    return await permissions.query({ name: "geolocation" as PermissionName });
  } catch {
    return undefined;
  }
}

type Teardown = {
  watchId?: number;
  watchdog?: ReturnType<typeof setTimeout>;
  permission?: PermissionStatus;
  onPermissionChange?: () => void;
};

function releaseWatch(handles: Teardown): void {
  if (handles.watchId !== undefined) {
    globalThis.navigator?.geolocation?.clearWatch(handles.watchId);
  }
  if (handles.watchdog !== undefined) clearTimeout(handles.watchdog);
  if (handles.permission && handles.onPermissionChange) {
    handles.permission.removeEventListener?.("change", handles.onPermissionChange);
  }
  handles.watchId = undefined;
  handles.watchdog = undefined;
  handles.permission = undefined;
  handles.onPermissionChange = undefined;
}

type Settle = (id: number, next: AcquisitionState) => void;

type Session = {
  state: AcquisitionState;
  setState: Dispatch<SetStateAction<AcquisitionState>>;
  handlesRef: MutableRefObject<Teardown>;
  requestIdRef: MutableRefObject<number>;
  stop: () => void;
  settle: Settle;
  cancel: () => void;
  hasResolved: boolean;
};

/**
 * Owns the acquisition snapshot and the request-supersession bookkeeping that
 * every other piece of the hook coordinates through.
 */
function useAcquisitionSession(): Session {
  const [state, setState] = useState<AcquisitionState>({
    status: "idle",
    permission: "unknown",
  });
  const handlesRef = useRef<Teardown>({});
  const requestIdRef = useRef(0);
  const [hasResolved, setHasResolved] = useState(false);

  const stop = useCallback(() => releaseWatch(handlesRef.current), []);

  const settle = useCallback<Settle>(
    (id, next) => {
      if (id !== requestIdRef.current) return;
      requestIdRef.current += 1;
      stop();
      setHasResolved(true);
      setState(next);
    },
    [stop],
  );

  const cancel = useCallback(() => {
    requestIdRef.current += 1;
    stop();
    setState((current) => ({ status: "idle", permission: current.permission }));
  }, [stop]);

  return { state, setState, handlesRef, requestIdRef, stop, settle, cancel, hasResolved };
}

function sampleHandler(settle: Settle, id: number): PositionCallback {
  return (sample) => {
    const position = readGuidanceSample(sample);
    if (!position) {
      settle(id, { status: "error", permission: "granted", error: { kind: "UNAVAILABLE" } });
      return;
    }
    settle(id, { status: "ready", permission: "granted", position });
  };
}

function failureHandler(
  settle: Settle,
  id: number,
  permission: AcquisitionPermission,
): PositionErrorCallback {
  return (failure) => {
    const kind = classifyAcquisitionError(failure);
    const resolved = kind === "PERMISSION_DENIED" ? "denied" : permission;
    settle(id, { status: "error", permission: resolved, error: { kind } });
  };
}

/**
 * Starts the single-shot watch behind an own watchdog: the W3C `timeout` does
 * not run while a permission prompt is open, so the acquisition would otherwise
 * be able to hang indefinitely (FR-003).
 */
function useWatchStarter({ handlesRef, settle }: Session) {
  return useCallback(
    (id: number, permission: AcquisitionPermission) => {
      const geolocation = globalThis.navigator?.geolocation;
      if (!geolocation) {
        settle(id, { status: "error", permission, error: { kind: "UNAVAILABLE" } });
        return;
      }
      handlesRef.current.watchdog = setTimeout(
        () => settle(id, { status: "error", permission, error: { kind: "TIMEOUT" } }),
        ACQUISITION_TIMEOUT_MS,
      );
      handlesRef.current.watchId = geolocation.watchPosition(
        sampleHandler(settle, id),
        failureHandler(settle, id, permission),
        ACQUISITION_OPTIONS,
      );
    },
    [handlesRef, settle],
  );
}

/** Promotes `prompting` to `acquiring` the moment the user grants permission. */
function usePermissionWatcher({ handlesRef, requestIdRef, setState }: Session) {
  return useCallback(
    (id: number, status: PermissionStatus) => {
      const onChange = () => {
        if (id !== requestIdRef.current) return;
        const permission = status.state as AcquisitionPermission;
        setState((current) =>
          current.status === "prompting" && permission === "granted"
            ? { ...current, status: "acquiring", permission }
            : { ...current, permission },
        );
      };
      handlesRef.current.permission = status;
      handlesRef.current.onPermissionChange = onChange;
      status.addEventListener?.("change", onChange);
    },
    [handlesRef, requestIdRef, setState],
  );
}

/**
 * Explicit, user-triggered acquisition. A newer request supersedes an in-flight
 * one: exactly one acquisition stays outstanding and a superseded result is
 * discarded even if it arrives first (FR-004).
 */
function useRefresh(
  session: Session,
  startWatch: ReturnType<typeof useWatchStarter>,
  watchPermissionGrant: ReturnType<typeof usePermissionWatcher>,
) {
  const { requestIdRef, setState, stop } = session;
  return useCallback(async () => {
    stop();
    requestIdRef.current += 1;
    const id = requestIdRef.current;
    setState((current) => ({ status: "prompting", permission: current.permission }));
    const status = await probePermission();
    if (id !== requestIdRef.current) return;
    const permission = (status?.state as AcquisitionPermission) ?? "unknown";
    if (status) watchPermissionGrant(id, status);
    setState({ status: permission === "granted" ? "acquiring" : "prompting", permission });
    startWatch(id, permission);
  }, [requestIdRef, setState, startWatch, stop, watchPermissionGrant]);
}

/** A backgrounded tab abandons the acquisition rather than resolving unseen. */
function useReleaseWhenHidden({ cancel, requestIdRef, stop }: Session): void {
  useEffect(() => {
    const onVisibility = () => {
      if (document.hidden) cancel();
    };
    document.addEventListener("visibilitychange", onVisibility);
    return () => {
      document.removeEventListener("visibilitychange", onVisibility);
      requestIdRef.current += 1;
      stop();
    };
  }, [cancel, requestIdRef, stop]);
}

export function useGuidancePosition() {
  const session = useAcquisitionSession();
  const startWatch = useWatchStarter(session);
  const watchPermissionGrant = usePermissionWatcher(session);
  const refresh = useRefresh(session, startWatch, watchPermissionGrant);

  useReleaseWhenHidden(session);

  return { ...session.state, refresh, cancel: session.cancel, hasResolved: session.hasResolved };
}

"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { getConfig, listLocations } from "@/features/locations/api/location-api";

import { rankNearby, type DirectoryRow } from "./nearby";
import type { NearbyEntry } from "./position-types";
import { useGuidancePosition } from "./use-guidance-position";

/** A reading older than this is labelled stale. Exactly this age is not yet stale. */
export const STALE_AFTER_SECONDS = 60;

const AGE_TICK_MS = 1000;
const MS_PER_SECOND = 1000;

export type ReferenceData = {
  locations: readonly DirectoryRow[];
  maxAccuracyM: number;
};

export type ReferenceState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "ready"; data: ReferenceData }
  | { status: "unavailable" };

/**
 * The preview verdict. `unevaluated` is a distinct outcome, not a degraded
 * evaluation: no default radius and no default accuracy threshold is ever
 * substituted for missing reference data (FR-021a).
 */
export type GuidanceEvaluation =
  | { status: "unevaluated"; reason: "REFERENCE_DATA_UNAVAILABLE" }
  | { status: "evaluated"; nearby: NearbyEntry[]; maxAccuracyM: number };

async function readReference(): Promise<ReferenceData> {
  const [locations, config] = await Promise.all([listLocations({ is_active: true }), getConfig()]);
  return { locations, maxAccuracyM: Number(config.max_attendance_accuracy_m) };
}

/**
 * Loads the Location directory and Config on demand. A failure of either read
 * is a single outcome — `unavailable` — kept apart from both the browser
 * acquisition vocabulary and the Attendance server codes (FR-008b).
 */
function useReferenceData() {
  const [reference, setReference] = useState<ReferenceState>({ status: "idle" });

  const loadReference = useCallback(async () => {
    setReference({ status: "loading" });
    try {
      setReference({ status: "ready", data: await readReference() });
    } catch {
      setReference({ status: "unavailable" });
    }
  }, []);

  return { reference, loadReference };
}

/**
 * Device-local elapsed time since the sample was captured, re-read once a
 * second. It is a display value only and gates no action (FR-005).
 */
function useAgeSeconds(capturedAt: string | undefined): number | undefined {
  const [now, setNow] = useState(0);

  useEffect(() => {
    if (!capturedAt) return;
    const tick = setInterval(() => setNow(Date.now()), AGE_TICK_MS);
    return () => clearInterval(tick);
  }, [capturedAt]);

  if (!capturedAt) return undefined;
  // Before the first tick — and immediately after a fresh sample supersedes an
  // older clock reading — the sample is by definition brand new.
  return Math.max(0, (now - Date.parse(capturedAt)) / MS_PER_SECOND);
}

function evaluate(
  reference: ReferenceState,
  position: Parameters<typeof rankNearby>[0] | undefined,
): GuidanceEvaluation | undefined {
  if (!position) return undefined;
  if (reference.status !== "ready") {
    return { status: "unevaluated", reason: "REFERENCE_DATA_UNAVAILABLE" };
  }
  return {
    status: "evaluated",
    nearby: rankNearby(position, reference.data.locations),
    maxAccuracyM: reference.data.maxAccuracyM,
  };
}

function pickFocused(
  evaluation: GuidanceEvaluation | undefined,
  focusedCode: string | undefined,
): NearbyEntry | undefined {
  if (evaluation?.status !== "evaluated") return undefined;
  return evaluation.nearby.find((entry) => entry.code === focusedCode) ?? evaluation.nearby[0];
}

/**
 * Composes acquisition, reference data, ranking and focus. Everything lives in
 * component memory: nothing is persisted and no coordinate leaves the device
 * (FR-034, FR-037).
 */
export function useGuidance() {
  const acquisition = useGuidancePosition();
  const { reference, loadReference } = useReferenceData();
  const [focusedCode, setFocusedCode] = useState<string | undefined>(undefined);

  const start = useCallback(() => {
    setFocusedCode(undefined);
    void loadReference();
    void acquisition.refresh();
  }, [acquisition, loadReference]);

  const ageSeconds = useAgeSeconds(acquisition.position?.capturedAt);
  const evaluation = useMemo(
    () => evaluate(reference, acquisition.position),
    [reference, acquisition.position],
  );

  return {
    ...acquisition,
    reference,
    evaluation,
    focused: pickFocused(evaluation, focusedCode),
    focus: setFocusedCode,
    ageSeconds,
    isStale: ageSeconds !== undefined && ageSeconds > STALE_AFTER_SECONDS,
    hasResolved: acquisition.hasResolved,
    start,
  };
}

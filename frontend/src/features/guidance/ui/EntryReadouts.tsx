"use client";

import { UI_MESSAGES } from "@/shared/messages";

import type { NearbyEntry } from "../model/position-types";
import { formatMetres } from "./format";

const TEXT = UI_MESSAGES.guidance;

/**
 * The per-Location readouts, factored out so the ranked list and the focused
 * target render byte-identical wording and so a later feature can reuse them
 * without copying the vocabulary (FR-043).
 */

/** `code` first: address and distance alone cannot tell coincident sites apart. */
export function EntryIdentity({ entry, suffix }: { entry: NearbyEntry; suffix?: string }) {
  return (
    <p>
      <strong>{entry.code}</strong> — {entry.name}
      {suffix ? ` (${suffix})` : ""}
    </p>
  );
}

export function DistanceReadout({ entry }: { entry: NearbyEntry }) {
  return (
    <p>
      {TEXT.distanceLabel}: {formatMetres(entry.distanceM)} — {TEXT.radiusLabel}:{" "}
      {formatMetres(entry.radiusM)}
    </p>
  );
}

/**
 * Membership is the closed two-value vocabulary of FR-015. There is no third
 * "uncertain" rendering, and `accuracyM` is never folded into it (FR-016).
 */
export function MembershipVerdict({ entry }: { entry: NearbyEntry }) {
  const inside = entry.status === "INSIDE_GEOFENCE";
  return (
    <p className={inside ? "verdict-ok" : "verdict-warn"}>{inside ? TEXT.inside : TEXT.outside}</p>
  );
}

/**
 * Distance to the boundary outside, remaining margin inside. Both are labelled
 * estimates for guidance and neither is a business acceptance rule (FR-018).
 */
export function BoundaryReadout({ entry }: { entry: NearbyEntry }) {
  const inside = entry.status === "INSIDE_GEOFENCE";
  const label = inside ? TEXT.insideMarginLabel : TEXT.distanceToBoundaryLabel;
  const value = inside ? entry.insideMarginM : entry.distanceToBoundaryM;
  return (
    <p>
      {label}: {formatMetres(value)} ({TEXT.estimateOnly})
    </p>
  );
}

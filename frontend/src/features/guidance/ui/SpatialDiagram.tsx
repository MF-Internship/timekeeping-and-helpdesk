"use client";

import { UI_MESSAGES } from "@/shared/messages";

import type { GuidancePosition, NearbyEntry } from "../model/position-types";
import { ScaleBar, SpatialLegend } from "./spatial/legend";
import {
  CurrentPositionMarker,
  NearbyLocationMarker,
  TargetLocationMarker,
} from "./spatial/markers";
import {
  fit,
  isOnCanvas,
  offsetOf,
  place,
  usableEntry,
  VIEWPORT,
  type Geometry,
} from "./spatial/projection";
import { GeofenceRadius, GpsAccuracyRadius } from "./spatial/radius-layers";

const TEXT = UI_MESSAGES.guidance;

function DiagramCanvas({
  position,
  entries,
  focused,
  geometry,
  onFocus,
}: {
  position: GuidancePosition;
  entries: readonly NearbyEntry[];
  focused: NearbyEntry;
  geometry: Geometry;
  onFocus(code: string): void;
}) {
  const others = entries
    .filter((entry) => entry.code !== focused.code && usableEntry(entry))
    .map((entry) => ({
      entry,
      point: place(offsetOf(position, entry.coordinates), geometry.scale),
    }))
    .filter(({ point }) => isOnCanvas(point));
  return (
    <svg viewBox={`0 0 ${VIEWPORT} ${VIEWPORT}`} width="100%" aria-label={TEXT.diagramHeading}>
      <GeofenceRadius entry={focused} point={geometry.target} scale={geometry.scale} />
      <TargetLocationMarker entry={focused} point={geometry.target} />
      {others.map(({ entry, point }) => (
        <NearbyLocationMarker key={entry.code} entry={entry} point={point} onFocus={onFocus} />
      ))}
      <GpsAccuracyRadius radius={geometry.accuracyR} />
      <CurrentPositionMarker />
      <ScaleBar scale={geometry.scale} />
    </svg>
  );
}

export type SpatialDiagramProps = {
  position?: GuidancePosition;
  entries: readonly NearbyEntry[];
  focused?: NearbyEntry;
  onFocus(code: string): void;
  busy: boolean;
};

export function SpatialDiagram({ position, entries, focused, onFocus, busy }: SpatialDiagramProps) {
  if (busy) return null;
  const geometry = fit(position, focused);
  return (
    <section aria-label={TEXT.diagramHeading}>
      <h3>{TEXT.diagramHeading}</h3>
      {geometry && position && focused ? (
        <DiagramCanvas
          position={position}
          entries={entries}
          focused={focused}
          geometry={geometry}
          onFocus={onFocus}
        />
      ) : (
        <p>{TEXT.diagramUnavailable}</p>
      )}
      <SpatialLegend hasOthers={entries.length > 1} />
      <p>{TEXT.diagramSelfContained}</p>
    </section>
  );
}

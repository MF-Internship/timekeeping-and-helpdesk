import { UI_MESSAGES } from "@/shared/messages";
import type { NearbyEntry } from "../../model/position-types";
import { CENTRE, type Point } from "./projection";

const TEXT = UI_MESSAGES.guidance;

export function GeofenceRadius({
  entry,
  point,
  scale,
}: {
  entry: NearbyEntry;
  point: Point;
  scale: number;
}) {
  return (
    <circle
      role="img"
      aria-label={`${TEXT.diagramGeofence}: ${entry.code}`}
      cx={point.x}
      cy={point.y}
      r={entry.radiusM * scale}
      fill="none"
      stroke="currentColor"
    />
  );
}

export function GpsAccuracyRadius({ radius }: { radius: number }) {
  return (
    <circle
      role="img"
      aria-label={TEXT.diagramAccuracy}
      cx={CENTRE}
      cy={CENTRE}
      r={radius}
      fill="none"
      stroke="currentColor"
      strokeDasharray="4 3"
    />
  );
}

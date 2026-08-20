import { UI_MESSAGES } from "@/shared/messages";
import type { NearbyEntry } from "../../model/position-types";
import { CENTRE, type Point } from "./projection";

const TEXT = UI_MESSAGES.guidance;
const POSITION_RADIUS = 5;
const TARGET_SIZE = 14;
const TARGET_RADIUS = TARGET_SIZE / 2;
const NEARBY_RADIUS = 4;
const TOUCH_RADIUS = 22;

export function CurrentPositionMarker() {
  return (
    <circle
      role="img"
      aria-label={TEXT.diagramYou}
      cx={CENTRE}
      cy={CENTRE}
      r={POSITION_RADIUS}
      fill="currentColor"
    />
  );
}

export function TargetLocationMarker({ entry, point }: { entry: NearbyEntry; point: Point }) {
  return (
    <rect
      role="img"
      aria-label={`${TEXT.diagramTarget}: ${entry.code}`}
      x={point.x - TARGET_RADIUS}
      y={point.y - TARGET_RADIUS}
      width={TARGET_SIZE}
      height={TARGET_SIZE}
      fill="currentColor"
    />
  );
}

export function NearbyLocationMarker({
  entry,
  point,
  onFocus,
}: {
  entry: NearbyEntry;
  point: Point;
  onFocus(code: string): void;
}) {
  const activate = () => onFocus(entry.code);
  return (
    <g
      role="button"
      tabIndex={0}
      aria-label={`${TEXT.diagramOther}: ${entry.code}`}
      onClick={activate}
      onKeyDown={(event) => ["Enter", " "].includes(event.key) && activate()}
    >
      <circle cx={point.x} cy={point.y} r={TOUCH_RADIUS} fill="transparent" />
      <circle
        cx={point.x}
        cy={point.y}
        r={NEARBY_RADIUS}
        fill="currentColor"
        fillOpacity="0.45"
        pointerEvents="none"
      />
    </g>
  );
}

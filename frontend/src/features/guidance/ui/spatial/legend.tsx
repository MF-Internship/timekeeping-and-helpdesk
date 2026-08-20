import { UI_MESSAGES } from "@/shared/messages";
import { formatMetres } from "../format";
import { PADDING, VIEWPORT } from "./projection";

const TEXT = UI_MESSAGES.guidance;
const SCALE_BAR_PX = 64;

export function ScaleBar({ scale }: { scale: number }) {
  const y = VIEWPORT - PADDING / 2;
  return (
    <g>
      <line x1={PADDING} x2={PADDING + SCALE_BAR_PX} y1={y} y2={y} stroke="currentColor" />
      <text x={PADDING} y={y - 6} fontSize={11}>
        {TEXT.diagramScaleLabel}: {formatMetres(SCALE_BAR_PX / scale)}
      </text>
    </g>
  );
}

export function SpatialLegend({ hasOthers }: { hasOthers: boolean }) {
  return (
    <ul className="record-list">
      <li>{TEXT.diagramYou}</li>
      <li>{TEXT.diagramTarget}</li>
      <li>{TEXT.diagramGeofence}</li>
      <li>
        {TEXT.diagramAccuracy} — {TEXT.diagramAccuracyDiagnostic}
      </li>
      {hasOthers && (
        <li>
          {TEXT.diagramOther} — {TEXT.diagramSelectHint}
        </li>
      )}
    </ul>
  );
}
